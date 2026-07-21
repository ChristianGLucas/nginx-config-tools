from gen.messages_pb2 import NginxConfig, DocumentRootList, DocumentRoot
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten

_ROOT_DIRECTIVES = {"root", "alias"}


def extract_document_roots(ax: AxiomContext, input: NginxConfig) -> DocumentRootList:
    """Extract every `root` and `alias` directive: which one it was, the
    filesystem path as written, and where it sits in the config.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return DocumentRootList(error=error)

    roots = []
    for d in flatten(directives):
        if d.name not in _ROOT_DIRECTIVES:
            continue
        path = d.args[0] if d.args else ""
        roots.append(
            DocumentRoot(
                directive=d.name,
                path=path,
                line=d.line,
                context_path=list(d.context_path),
            )
        )
    return DocumentRootList(roots=roots)
