from gen.messages_pb2 import NginxConfig
from nodes.extract_listen_directives import extract_listen_directives
from nodes._test_fixtures import SAMPLE_CONFIG
from gen.axiom_context import SecretStatus


class _TestContext:
    class _Logger:
        def debug(self, msg, **a): pass
        def info(self, msg, **a): pass
        def warn(self, msg, **a): pass
        def error(self, msg, **a): pass

    class _Secrets:
        def __init__(self, m, revoked):
            self._m = m or {}
            self._revoked = revoked or set()
        def get(self, name):
            v = self._m.get(name)
            return (v, True) if v is not None else ("", False)
        def status(self, name):
            if name in self._m:
                return SecretStatus.AVAILABLE
            if name in self._revoked:
                return SecretStatus.REVOKED
            return SecretStatus.UNSET

    def __init__(self, secrets_map=None, revoked_names=None):
        self.log = self._Logger()
        self.secrets = self._Secrets(secrets_map, revoked_names)
        self.execution_id = "test-execution-id"
        self.flow_id = "test-flow-id"
        self.tenant_id = "test-tenant-id"


def test_extract_listen_directives_golden():
    ax = _TestContext()
    result = extract_listen_directives(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.listens) == 2
    l0, l1 = result.listens
    assert l0.address == "" and l0.port == 80 and l0.default_server is True
    assert l1.address == "[::]" and l1.port == 443 and l1.ssl is True and l1.http2 is True


def test_extract_listen_directives_unix_socket_and_bare_ipv4_port():
    ax = _TestContext()
    text = (
        "http {\n"
        "  server {\n"
        "    listen unix:/var/run/nginx.sock;\n"
        "    listen 127.0.0.1:8080;\n"
        "  }\n"
        "}\n"
    )
    result = extract_listen_directives(ax, NginxConfig(config=text))
    assert len(result.listens) == 2
    assert result.listens[0].address == "unix:/var/run/nginx.sock"
    assert result.listens[0].port == 0
    assert result.listens[1].address == "127.0.0.1"
    assert result.listens[1].port == 8080
