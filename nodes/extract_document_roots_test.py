from gen.messages_pb2 import NginxConfig
from nodes.extract_document_roots import extract_document_roots
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


def test_extract_document_roots_golden():
    ax = _TestContext()
    result = extract_document_roots(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.roots) == 1
    r = result.roots[0]
    assert r.directive == "root"
    assert r.path == "/var/www/html"
    assert list(r.context_path) == ["http", "server"]


def test_extract_document_roots_alias_too():
    ax = _TestContext()
    text = "http {\n  server {\n    location /static/ {\n      alias /data/static/;\n    }\n  }\n}\n"
    result = extract_document_roots(ax, NginxConfig(config=text))
    assert len(result.roots) == 1
    assert result.roots[0].directive == "alias"
    assert result.roots[0].path == "/data/static/"
