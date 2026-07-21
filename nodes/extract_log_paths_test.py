from gen.messages_pb2 import NginxConfig
from nodes.extract_log_paths import extract_log_paths
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


def test_extract_log_paths_golden():
    ax = _TestContext()
    result = extract_log_paths(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.logs) == 2
    by_directive = {l.directive: (l.path, l.format_or_level) for l in result.logs}
    assert by_directive["access_log"] == ("/var/log/nginx/access.log", "combined")
    assert by_directive["error_log"] == ("/var/log/nginx/error.log", "warn")


def test_extract_log_paths_access_log_off():
    ax = _TestContext()
    text = "http {\n  server {\n    access_log off;\n  }\n}\n"
    result = extract_log_paths(ax, NginxConfig(config=text))
    assert len(result.logs) == 1
    assert result.logs[0].path == "off"
