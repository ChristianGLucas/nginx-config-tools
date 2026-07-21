from gen.messages_pb2 import NginxConfig, IncludeList, IncludeDirective
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def extract_includes(ax: AxiomContext, input: NginxConfig) -> IncludeList:
    """Extract every `include` directive's path and location in the
    config. Paths are reported as data only — this node never opens,
    globs, or fetches them.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return IncludeList(error=error)

    includes = []
    for d in flatten(directives):
        if d.name != "include":
            continue
        path = d.args[0] if d.args else ""
        includes.append(
            IncludeDirective(path=path, line=d.line, context_path=list(d.context_path))
        )
    return IncludeList(includes=includes)
