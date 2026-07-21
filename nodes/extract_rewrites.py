from gen.messages_pb2 import NginxConfig, RewriteList, RewriteRule, ReturnDirective
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def extract_rewrites(ax: AxiomContext, input: NginxConfig) -> RewriteList:
    """Extract every `rewrite` directive (regex, replacement, optional
    last/break/redirect/permanent flag) and every `return` directive
    (status code and optional URL/body text) in the config.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return RewriteList(error=error)

    rewrites = []
    returns = []
    for d in flatten(directives):
        if d.name == "rewrite":
            args = list(d.args)
            regex = args[0] if len(args) > 0 else ""
            replacement = args[1] if len(args) > 1 else ""
            flag = args[2] if len(args) > 2 else ""
            rewrites.append(
                RewriteRule(
                    regex=regex,
                    replacement=replacement,
                    flag=flag,
                    line=d.line,
                    context_path=list(d.context_path),
                )
            )
        elif d.name == "return":
            args = list(d.args)
            code = args[0] if len(args) > 0 else ""
            text = " ".join(args[1:]) if len(args) > 1 else ""
            returns.append(
                ReturnDirective(
                    code=code,
                    text=text,
                    line=d.line,
                    context_path=list(d.context_path),
                )
            )
    return RewriteList(rewrites=rewrites, returns=returns)
