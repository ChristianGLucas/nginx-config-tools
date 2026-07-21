from gen.messages_pb2 import NginxConfig
from nodes.extract_proxy_targets import extract_proxy_targets
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


def test_extract_proxy_targets_golden():
    ax = _TestContext()
    result = extract_proxy_targets(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.targets) == 2
    by_directive = {t.directive: t.target for t in result.targets}
    assert by_directive["proxy_pass"] == "http://$upstream_name"
    assert by_directive["fastcgi_pass"] == "127.0.0.1:9000"
    for t in result.targets:
        assert list(t.context_path) == ["http", "server", "location"]


def test_extract_proxy_targets_none_present():
    ax = _TestContext()
    result = extract_proxy_targets(ax, NginxConfig(config="http { server { } }\n"))
    assert result.error == ""
    assert len(result.targets) == 0
