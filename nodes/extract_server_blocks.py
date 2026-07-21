from gen.messages_pb2 import NginxConfig, ServerBlockList, ServerBlock, ListenSpec
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten, parse_listen_args


def extract_server_blocks(ax: AxiomContext, input: NginxConfig) -> ServerBlockList:
    """Extract every `server { ... }` block in the config: its decomposed
    listen specs, its server_name values, its starting line, and its
    immediate directives.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return ServerBlockList(error=error)

    servers = []
    for d in flatten(directives):
        if d.name != "server" or not d.is_block:
            continue
        listens = []
        server_names = []
        for c in d.children:
            if c.name == "listen":
                address, port, ssl, http2, default_server = parse_listen_args(list(c.args))
                listens.append(
                    ListenSpec(
                        address=address,
                        port=port,
                        ssl=ssl,
                        http2=http2,
                        default_server=default_server,
                        raw=" ".join(c.args),
                        line=c.line,
                        context_path=list(c.context_path),
                    )
                )
            elif c.name == "server_name":
                server_names.extend(c.args)
        servers.append(
            ServerBlock(
                listen=listens,
                server_names=server_names,
                line=d.line,
                directives=list(d.children),
            )
        )
    return ServerBlockList(servers=servers)
