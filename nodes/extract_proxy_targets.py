from gen.messages_pb2 import NginxConfig, ProxyTargetList, ProxyTarget
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten

_PROXY_DIRECTIVES = {"proxy_pass", "fastcgi_pass"}


def extract_proxy_targets(ax: AxiomContext, input: NginxConfig) -> ProxyTargetList:
    """Extract every `proxy_pass` and `fastcgi_pass` directive: which
    directive it was, its target as written (an upstream name, URL, or
    host:port), and where it sits in the config — the routing/backend map
    for understanding traffic flow.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return ProxyTargetList(error=error)

    targets = []
    for d in flatten(directives):
        if d.name not in _PROXY_DIRECTIVES:
            continue
        target = d.args[0] if d.args else ""
        targets.append(
            ProxyTarget(
                directive=d.name,
                target=target,
                line=d.line,
                context_path=list(d.context_path),
            )
        )
    return ProxyTargetList(targets=targets)
