from gen.messages_pb2 import NginxConfig
from nodes.extract_location_blocks import extract_location_blocks
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


def test_extract_location_blocks_golden():
    ax = _TestContext()
    result = extract_location_blocks(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.locations) == 4
    mods = {(loc.modifier, loc.path) for loc in result.locations}
    assert ("", "/") in mods
    assert ("~*", "\\.php$") in mods
    assert ("^~", "/api/") in mods
    assert ("=", "/health") in mods
    for loc in result.locations:
        assert list(loc.server_names) == ["example.com", "www.example.com"]


def test_extract_location_blocks_no_enclosing_server_has_empty_server_names():
    ax = _TestContext()
    text = "http {\n  location / {\n    root /var/www;\n  }\n}\n"
    result = extract_location_blocks(ax, NginxConfig(config=text))
    assert result.error == ""
    assert len(result.locations) == 1
    assert list(result.locations[0].server_names) == []
    assert result.locations[0].modifier == ""
    assert result.locations[0].path == "/"
