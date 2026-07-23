from gen.messages_pb2 import NginxConfig
from nodes.extract_server_blocks import extract_server_blocks
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


def test_extract_server_blocks_golden():
    ax = _TestContext()
    result = extract_server_blocks(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.servers) == 1
    s = result.servers[0]
    assert list(s.server_names) == ["example.com", "www.example.com"]
    assert len(s.listen) == 2
    l0, l1 = s.listen
    assert l0.address == "" and l0.port == 80 and l0.default_server is True
    assert l0.ssl is False and l0.http2 is False
    assert l1.address == "[::]" and l1.port == 443 and l1.ssl is True and l1.http2 is True
    directive_names = {d.name for d in s.directives}
    assert "location" in directive_names
    assert "root" in directive_names


def test_extract_server_blocks_no_servers_returns_empty_list():
    ax = _TestContext()
    result = extract_server_blocks(ax, NginxConfig(config="events {}\n"))
    assert result.error == ""
    assert len(result.servers) == 0
