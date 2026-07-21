from gen.messages_pb2 import NginxConfig, DirectiveList
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def list_directives(ax: AxiomContext, input: NginxConfig) -> DirectiveList:
    """Flatten the parsed directive tree (top-level and every nested
    directive) into a single ordered list, each entry carrying its own
    context_path. Useful for a full inventory or for filtering by directive
    name across the whole config.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return DirectiveList(error=error)
    return DirectiveList(directives=list(flatten(directives)))
