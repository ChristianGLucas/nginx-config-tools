from gen.messages_pb2 import NginxConfig, VariableUsageList, VariableUsage
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten, find_vars


def extract_variables(ax: AxiomContext, input: NginxConfig) -> VariableUsageList:
    """Extract every nginx variable touchpoint in the config: `set $name
    value;` declarations, and every `$name` reference found inside any
    other directive's arguments (e.g. inside proxy_pass, log_format,
    return) — including references inside a larger string like
    "$scheme://$host".
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return VariableUsageList(error=error)

    usages = []
    for d in flatten(directives):
        args = list(d.args)
        if d.name == "set":
            var_name = args[0].lstrip("$") if args else ""
            value = args[1] if len(args) > 1 else ""
            usages.append(
                VariableUsage(
                    name=var_name,
                    kind="set",
                    value=value,
                    line=d.line,
                    context_path=list(d.context_path),
                )
            )
            # scan the value for further $var references, not the LHS name
            scan_args = args[1:]
        else:
            scan_args = args
        for var_name in find_vars(scan_args):
            usages.append(
                VariableUsage(
                    name=var_name,
                    kind="usage",
                    value=d.name,
                    line=d.line,
                    context_path=list(d.context_path),
                )
            )
    return VariableUsageList(variables=usages)
