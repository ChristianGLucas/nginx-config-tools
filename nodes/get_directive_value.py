from gen.messages_pb2 import GetDirectiveValueInput, DirectiveValueList
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def get_directive_value(ax: AxiomContext, input: GetDirectiveValueInput) -> DirectiveValueList:
    """Look up every directive matching a given name, optionally scoped to
    an exact context_path (e.g. only "listen" directives inside ["http",
    "server"]). Returns the matching directives with their full arguments
    and location — the general-purpose lookup for any directive this
    package has no dedicated Extract* node for.
    """
    directives, _issues, _valid, error = resolve(input.nginx_config)
    if error:
        return DirectiveValueList(error=error)

    ctx_filter = list(input.context_path) if len(input.context_path) > 0 else None
    matches = []
    for d in flatten(directives):
        if d.name != input.directive_name:
            continue
        if ctx_filter is not None and list(d.context_path) != ctx_filter:
            continue
        matches.append(d)
    return DirectiveValueList(matches=matches)
