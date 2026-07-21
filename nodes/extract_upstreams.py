from gen.messages_pb2 import NginxConfig, UpstreamList, Upstream, UpstreamServer
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten, UPSTREAM_METHOD_DIRECTIVES


def extract_upstreams(ax: AxiomContext, input: NginxConfig) -> UpstreamList:
    """Extract every `upstream <name> { ... }` block: its member `server`
    lines (address + trailing params like weight=/backup/down verbatim),
    and its load-balancing method (round_robin, least_conn, ip_hash, hash,
    or random) inferred from which method directive is present.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return UpstreamList(error=error)

    upstreams = []
    for d in flatten(directives):
        if d.name != "upstream" or not d.is_block:
            continue
        name = d.args[0] if d.args else ""
        members = []
        method = "round_robin"
        for c in d.children:
            if c.name == "server":
                address = c.args[0] if c.args else ""
                members.append(
                    UpstreamServer(address=address, params=list(c.args[1:]), line=c.line)
                )
            elif c.name in UPSTREAM_METHOD_DIRECTIVES:
                method = c.name
        upstreams.append(Upstream(name=name, servers=members, method=method, line=d.line))
    return UpstreamList(upstreams=upstreams)
