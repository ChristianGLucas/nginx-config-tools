from gen.messages_pb2 import NginxConfig
from nodes.summarize_config import summarize_config
from nodes._test_fixtures import SAMPLE_CONFIG, MALFORMED_CONFIG
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


def test_summarize_config_golden():
    ax = _TestContext()
    result = summarize_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert result.server_count == 1
    assert result.location_count == 4
    assert result.upstream_count == 1
    assert result.error_count == 0
    assert result.warning_count == 0
    assert list(result.server_names) == ["example.com", "www.example.com"]
    assert result.block_counts["server"] == 1
    assert result.block_counts["location"] == 4
    assert result.block_counts["upstream"] == 1
    assert result.block_counts["http"] == 1
    assert result.block_counts["events"] == 1
    # http(depth0) -> server(depth1) -> location(depth2) -> a directive
    # inside a location, e.g. proxy_pass or try_files (depth3)
    assert result.max_depth == 3
    # total_directives must equal what ListDirectives (a separately-tested
    # node) reports for the same input — a cross-node consistency oracle
    from nodes.list_directives import list_directives
    ld = list_directives(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.total_directives == len(ld.directives)


def test_summarize_config_counts_malformed_issues():
    ax = _TestContext()
    result = summarize_config(ax, NginxConfig(config=MALFORMED_CONFIG))
    assert result.error == ""
    assert result.error_count >= 1


def test_summarize_config_error_path():
    ax = _TestContext()
    huge = "http {\n" + ("  # pad\n" * (MAX_CONFIG_BYTES // 8 + 100)) + "}\n"
    result = summarize_config(ax, NginxConfig(config=huge))
    assert result.error != ""
    assert result.total_directives == 0
