from gen.messages_pb2 import NginxConfig
from nodes.extract_server_names import extract_server_names
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


def test_extract_server_names_golden():
    ax = _TestContext()
    result = extract_server_names(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.server_names) == 2
    names = [(e.name, e.server_line) for e in result.server_names]
    assert names[0][0] == "example.com"
    assert names[1][0] == "www.example.com"
    assert names[0][1] == names[1][1]  # same server block


def test_extract_server_names_multiple_servers_distinguished_by_line():
    ax = _TestContext()
    text = (
        "http {\n"
        "  server {\n"
        "    server_name a.example.com;\n"
        "  }\n"
        "  server {\n"
        "    server_name b.example.com;\n"
        "  }\n"
        "}\n"
    )
    result = extract_server_names(ax, NginxConfig(config=text))
    assert len(result.server_names) == 2
    assert result.server_names[0].name == "a.example.com"
    assert result.server_names[1].name == "b.example.com"
    assert result.server_names[0].server_line != result.server_names[1].server_line
