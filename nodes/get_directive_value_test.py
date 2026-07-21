from gen.messages_pb2 import NginxConfig, GetDirectiveValueInput
from nodes.get_directive_value import get_directive_value
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


def test_get_directive_value_unscoped():
    ax = _TestContext()
    cfg = NginxConfig(config=SAMPLE_CONFIG)
    result = get_directive_value(
        ax, GetDirectiveValueInput(nginx_config=cfg, directive_name="listen")
    )
    assert result.error == ""
    assert len(result.matches) == 2


def test_get_directive_value_scoped_to_exact_context_path():
    ax = _TestContext()
    cfg = NginxConfig(config=SAMPLE_CONFIG)
    result = get_directive_value(
        ax,
        GetDirectiveValueInput(
            nginx_config=cfg,
            directive_name="server",
            context_path=["http"],
        ),
    )
    assert len(result.matches) == 1  # the server block itself, context ["http"]

    # "least_conn" lives inside upstream, not server -> no match under ["http","server"]
    none_result = get_directive_value(
        ax,
        GetDirectiveValueInput(
            nginx_config=cfg,
            directive_name="least_conn",
            context_path=["http", "server"],
        ),
    )
    assert len(none_result.matches) == 0


def test_get_directive_value_no_match_returns_empty_not_error():
    ax = _TestContext()
    cfg = NginxConfig(config=SAMPLE_CONFIG)
    result = get_directive_value(
        ax, GetDirectiveValueInput(nginx_config=cfg, directive_name="does_not_exist")
    )
    assert result.error == ""
    assert len(result.matches) == 0
