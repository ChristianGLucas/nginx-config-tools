from gen.messages_pb2 import NginxConfig
from nodes.extract_rewrites import extract_rewrites
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


def test_extract_rewrites_golden():
    ax = _TestContext()
    result = extract_rewrites(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.rewrites) == 1
    rw = result.rewrites[0]
    assert rw.regex == "^/old/(.*)$"
    assert rw.replacement == "/new/$1"
    assert rw.flag == "permanent"

    assert len(result.returns) == 2
    codes = {r.code: r.text for r in result.returns}
    assert codes["200"] == "ok"
    assert codes["405"] == ""


def test_extract_rewrites_none_present():
    ax = _TestContext()
    result = extract_rewrites(ax, NginxConfig(config="http { server { } }\n"))
    assert result.error == ""
    assert len(result.rewrites) == 0
    assert len(result.returns) == 0
