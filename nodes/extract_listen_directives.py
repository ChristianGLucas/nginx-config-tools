from gen.messages_pb2 import NginxConfig, ListenList, ListenSpec
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten, parse_listen_args


def extract_listen_directives(ax: AxiomContext, input: NginxConfig) -> ListenList:
    """Extract and decompose every `listen` directive in the config:
    address, port, and the ssl/http2/default_server flags, plus the
    original argument list verbatim.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return ListenList(error=error)

    listens = []
    for d in flatten(directives):
        if d.name != "listen":
            continue
        address, port, ssl, http2, default_server = parse_listen_args(list(d.args))
        listens.append(
            ListenSpec(
                address=address,
                port=port,
                ssl=ssl,
                http2=http2,
                default_server=default_server,
                raw=" ".join(d.args),
                line=d.line,
                context_path=list(d.context_path),
            )
        )
    return ListenList(listens=listens)
