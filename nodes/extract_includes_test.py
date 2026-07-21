from gen.messages_pb2 import NginxConfig
from nodes.extract_includes import extract_includes
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


def test_extract_includes_golden():
    ax = _TestContext()
    result = extract_includes(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.includes) == 2
    paths = {i.path for i in result.includes}
    assert paths == {"/etc/nginx/mime.types", "/etc/nginx/conf.d/extra.conf"}


def test_extract_includes_never_touches_the_filesystem():
    ax = _TestContext()
    text = "http {\n  include /this/definitely/does/not/exist/anywhere.conf;\n}\n"
    result = extract_includes(ax, NginxConfig(config=text))
    # A missing target must not surface as an error — it is never opened.
    assert result.error == ""
    assert len(result.includes) == 1
    assert result.includes[0].path == "/this/definitely/does/not/exist/anywhere.conf"
