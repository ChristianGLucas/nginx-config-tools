from gen.messages_pb2 import NginxConfig, SSLConfigList, SSLConfig
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def extract_ssl_config(ax: AxiomContext, input: NginxConfig) -> SSLConfigList:
    """Extract SSL/TLS configuration per server block: ssl_certificate,
    ssl_certificate_key, ssl_protocols, and ssl_ciphers, tied to that
    server's server_name values. A server block is only included if it
    declares at least one of these four directives — a plain non-TLS
    server contributes nothing here.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return SSLConfigList(error=error)

    configs = []
    for d in flatten(directives):
        if d.name != "server" or not d.is_block:
            continue
        server_names = []
        certificate = ""
        certificate_key = ""
        protocols = []
        ciphers = ""
        found = False
        for c in d.children:
            if c.name == "server_name":
                server_names.extend(c.args)
            elif c.name == "ssl_certificate":
                certificate = c.args[0] if c.args else ""
                found = True
            elif c.name == "ssl_certificate_key":
                certificate_key = c.args[0] if c.args else ""
                found = True
            elif c.name == "ssl_protocols":
                protocols = list(c.args)
                found = True
            elif c.name == "ssl_ciphers":
                ciphers = c.args[0] if c.args else ""
                found = True
        if found:
            configs.append(
                SSLConfig(
                    server_names=server_names,
                    certificate=certificate,
                    certificate_key=certificate_key,
                    protocols=protocols,
                    ciphers=ciphers,
                    line=d.line,
                )
            )
    return SSLConfigList(configs=configs)
