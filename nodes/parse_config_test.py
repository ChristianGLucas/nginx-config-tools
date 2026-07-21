from gen.messages_pb2 import NginxConfig
from nodes.parse_config import parse_config
from nodes.nginx_parse import MAX_CONFIG_BYTES, MAX_NESTING_DEPTH
from nodes._test_fixtures import SAMPLE_CONFIG, MALFORMED_CONFIG
from gen.axiom_context import SecretStatus


class _TestContext:
    class _Logger:
        def debug(self, msg: str, **attrs) -> None: pass
        def info(self, msg: str, **attrs) -> None: pass
        def warn(self, msg: str, **attrs) -> None: pass
        def error(self, msg: str, **attrs) -> None: pass

    class _Secrets:
        def __init__(self, m: dict, revoked: set) -> None:
            self._m = m or {}
            self._revoked = revoked or set()
        def get(self, name: str):
            v = self._m.get(name)
            return (v, True) if v is not None else ("", False)
        def status(self, name: str) -> SecretStatus:
            if name in self._m:
                return SecretStatus.AVAILABLE
            if name in self._revoked:
                return SecretStatus.REVOKED
            return SecretStatus.UNSET

    def __init__(self, secrets_map: dict | None = None, revoked_names: set | None = None) -> None:
        self.log = self._Logger()
        self.secrets = self._Secrets(secrets_map or {}, revoked_names)
        self.execution_id = "test-execution-id"
        self.flow_id = "test-flow-id"
        self.tenant_id = "test-tenant-id"


def test_parse_config_golden():
    ax = _TestContext()
    result = parse_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.valid is True
    assert result.error == ""
    assert len(result.issues) == 0
    # top-level: user, worker_processes, events, http
    top_names = [d.name for d in result.directives]
    assert top_names == ["user", "worker_processes", "events", "http"]
    http = [d for d in result.directives if d.name == "http"][0]
    assert http.is_block is True
    assert list(http.context_path) == []
    server = [d for d in http.children if d.name == "server"][0]
    assert list(server.context_path) == ["http"]
    location = [d for d in server.children if d.name == "location"][0]
    assert list(location.context_path) == ["http", "server"]


def test_parse_config_missing_semicolon_before_next_directive_is_flagged_not_silently_merged():
    # Regression test for a CRITICAL finding from independent review: with
    # crossplane's own check_args=False, "listen 80" (missing ";") directly
    # followed by "location / {" got silently absorbed as if it were
    # `listen 80 location /` — three args, no error, valid=True — instead
    # of surfacing the caller's typo as a structural issue. This is one of
    # the single most common real nginx.conf mistakes, so it must be caught.
    ax = _TestContext()
    text = (
        "http {\n"
        "  server {\n"
        "    listen 80\n"
        "    location / {\n"
        "      root /var/www;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    result = parse_config(ax, NginxConfig(config=text))
    assert result.valid is False
    assert len(result.issues) >= 1
    assert result.issues[0].line == 3
    assert "not terminated" in result.issues[0].message
    # and, just as importantly: no directive anywhere in whatever WAS
    # parsed should show "listen" with "location"/"/" merged into its args
    from nodes.nginx_parse import flatten

    for d in flatten(list(result.directives)):
        if d.name == "listen":
            assert "location" not in list(d.args)


def test_parse_config_malformed_reports_structured_issue_not_crash():
    ax = _TestContext()
    result = parse_config(ax, NginxConfig(config=MALFORMED_CONFIG))
    assert result.error == ""  # not a hard failure — a best-effort parse
    assert result.valid is False
    assert len(result.issues) >= 1
    # The missing ";" is on line 3 ("listen 80" with no terminator before
    # the next directive) — arg-count/terminator validation catches it
    # exactly there, not at EOF.
    assert result.issues[0].line == 3
    assert "not terminated" in result.issues[0].message
    assert result.issues[0].severity == "error"
    # message must never leak the internal temp file path used to satisfy
    # crossplane's file-based API — and must be stable across calls (see
    # determinism test below), so it cannot contain a per-call random name
    assert "/tmp/" not in result.issues[0].message
    assert ".conf" not in result.issues[0].message


def test_parse_config_is_deterministic_across_repeated_calls():
    ax = _TestContext()
    first = parse_config(ax, NginxConfig(config=MALFORMED_CONFIG))
    second = parse_config(ax, NginxConfig(config=MALFORMED_CONFIG))
    assert first.issues[0].message == second.issues[0].message
    assert first.issues[0].line == second.issues[0].line

    ok_first = parse_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    ok_second = parse_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert list(ok_first.directives) == list(ok_second.directives)


def test_parse_config_oversized_input_rejected_without_crash():
    ax = _TestContext()
    huge = "http {\n" + ("  # pad\n" * (MAX_CONFIG_BYTES // 8 + 100)) + "}\n"
    assert len(huge.encode("utf-8")) > MAX_CONFIG_BYTES
    result = parse_config(ax, NginxConfig(config=huge))
    assert result.error != ""
    assert "byte" in result.error or "exceeds" in result.error
    assert len(result.directives) == 0


def test_parse_config_deep_nesting_rejected_without_crash():
    ax = _TestContext()
    deep = "http {\n" + ("a {\n" * (MAX_NESTING_DEPTH + 50)) + ("}\n" * (MAX_NESTING_DEPTH + 50)) + "}\n"
    result = parse_config(ax, NginxConfig(config=deep))
    assert result.error != ""
    assert "nesting" in result.error
    assert len(result.directives) == 0


def test_parse_config_empty_input_is_valid_and_empty():
    ax = _TestContext()
    result = parse_config(ax, NginxConfig(config=""))
    assert result.valid is True
    assert result.error == ""
    assert len(result.directives) == 0


def test_parse_config_never_opens_a_missing_include_target():
    ax = _TestContext()
    text = "http {\n  include /this/path/does/not/exist/on/disk.conf;\n}\n"
    result = parse_config(ax, NginxConfig(config=text))
    # If this node tried to open() the include path (as crossplane does by
    # default with single=False), a missing file would surface as an issue.
    # It must not: include paths are reported as data only, never fetched.
    assert result.valid is True
    assert result.error == ""
    assert len(result.issues) == 0
