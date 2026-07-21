from gen.messages_pb2 import NginxConfig
from nodes.extract_variables import extract_variables
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


def test_extract_variables_golden():
    ax = _TestContext()
    result = extract_variables(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""

    sets = [v for v in result.variables if v.kind == "set"]
    assert len(sets) == 1
    assert sets[0].name == "upstream_name"
    assert sets[0].value == "backend"

    usages = [v for v in result.variables if v.kind == "usage"]
    usage_names = [u.name for u in usages]
    # $uri appears twice in "try_files $uri $uri/ =404;"
    assert usage_names.count("uri") == 2
    # $upstream_name referenced inside "http://$upstream_name" (embedded,
    # not standalone) must still be found
    assert "upstream_name" in usage_names
    assert "host" in usage_names
    assert "request_method" in usage_names
    proxy_pass_usage = [u for u in usages if u.name == "upstream_name"][0]
    assert proxy_pass_usage.value == "proxy_pass"  # names the directive it appeared in


def test_extract_variables_set_lhs_not_double_counted_as_usage():
    ax = _TestContext()
    text = "http {\n  server {\n    set $foo bar;\n  }\n}\n"
    result = extract_variables(ax, NginxConfig(config=text))
    names_kinds = [(v.name, v.kind) for v in result.variables]
    assert names_kinds == [("foo", "set")]  # not also ("foo", "usage")
