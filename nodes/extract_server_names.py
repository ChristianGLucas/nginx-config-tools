from gen.messages_pb2 import NginxConfig, ServerNameList, ServerNameEntry
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def extract_server_names(ax: AxiomContext, input: NginxConfig) -> ServerNameList:
    """Extract every `server_name` value declared anywhere in the config —
    the virtual-host inventory — each tied to the starting line of the
    server block that declared it.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return ServerNameList(error=error)

    entries = []
    for d in flatten(directives):
        if d.name != "server" or not d.is_block:
            continue
        for c in d.children:
            if c.name == "server_name":
                for name in c.args:
                    entries.append(ServerNameEntry(name=name, server_line=d.line))
    return ServerNameList(server_names=entries)
