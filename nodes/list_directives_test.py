from gen.messages_pb2 import NginxConfig
from nodes.list_directives import list_directives
from nodes.parse_config import parse_config
from nodes._test_fixtures import SAMPLE_CONFIG
from nodes.nginx_parse import MAX_CONFIG_BYTES
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


def test_list_directives_flattens_every_level():
    ax = _TestContext()
    result = list_directives(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    names = [d.name for d in result.directives]
    for expected in ("user", "worker_processes", "events", "http"):
        assert expected in names
    # nested (proves it's flattened, not just the top level)
    for expected in ("upstream", "server", "listen", "location", "proxy_pass"):
        assert expected in names
    nested = [d for d in result.directives if d.name == "proxy_pass"]
    assert len(nested) == 1
    assert list(nested[0].context_path) == ["http", "server", "location"]


def test_list_directives_error_path():
    ax = _TestContext()
    huge = "http {\n" + ("  # pad\n" * (MAX_CONFIG_BYTES // 8 + 100)) + "}\n"
    result = list_directives(ax, NginxConfig(config=huge))
    assert result.error != ""
    assert len(result.directives) == 0


def test_list_directives_chains_after_parse_config_without_reparsing():
    ax = _TestContext()
    parsed = parse_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    chained = list_directives(ax, parsed)
    standalone = list_directives(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert list(chained.directives) == list(standalone.directives)
