from gen.messages_pb2 import NginxConfig
from nodes.validate_structure import validate_structure
from nodes._test_fixtures import SAMPLE_CONFIG, MALFORMED_CONFIG
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


def test_validate_structure_clean_config():
    ax = _TestContext()
    result = validate_structure(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.valid is True
    assert len(result.issues) == 0


def test_validate_structure_reports_line_number_on_unterminated_directive():
    ax = _TestContext()
    result = validate_structure(ax, NginxConfig(config=MALFORMED_CONFIG))
    assert result.valid is False
    assert len(result.issues) >= 1
    # See parse_config_test.py: the missing ";" on line 3 is caught exactly
    # there by arg-count/terminator validation.
    assert result.issues[0].line == 3
    assert result.issues[0].severity == "error"


def test_validate_structure_unbalanced_braces():
    ax = _TestContext()
    text = "http {\n  server {\n    listen 80;\n"  # missing both closing braces
    result = validate_structure(ax, NginxConfig(config=text))
    assert result.valid is False
    assert len(result.issues) >= 1
