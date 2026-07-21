from gen.messages_pb2 import NginxConfig
from nodes.extract_upstreams import extract_upstreams
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


def test_extract_upstreams_golden():
    ax = _TestContext()
    result = extract_upstreams(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.upstreams) == 1
    u = result.upstreams[0]
    assert u.name == "backend"
    assert u.method == "least_conn"
    assert len(u.servers) == 3
    assert u.servers[0].address == "10.0.0.1:8080"
    assert list(u.servers[0].params) == ["weight=3"]
    assert u.servers[1].address == "10.0.0.2:8080"
    assert list(u.servers[1].params) == []
    assert u.servers[2].address == "10.0.0.3:8080"
    assert list(u.servers[2].params) == ["backup"]


def test_extract_upstreams_defaults_to_round_robin_when_no_method_directive():
    ax = _TestContext()
    text = "http {\n  upstream plain {\n    server 10.0.0.1;\n    server 10.0.0.2;\n  }\n}\n"
    result = extract_upstreams(ax, NginxConfig(config=text))
    assert len(result.upstreams) == 1
    assert result.upstreams[0].method == "round_robin"
