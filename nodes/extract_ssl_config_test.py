from gen.messages_pb2 import NginxConfig
from nodes.extract_ssl_config import extract_ssl_config
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


def test_extract_ssl_config_golden():
    ax = _TestContext()
    result = extract_ssl_config(ax, NginxConfig(config=SAMPLE_CONFIG))
    assert result.error == ""
    assert len(result.configs) == 1
    c = result.configs[0]
    assert c.certificate == "/etc/ssl/certs/example.crt"
    assert c.certificate_key == "/etc/ssl/private/example.key"
    assert list(c.protocols) == ["TLSv1.2", "TLSv1.3"]
    assert list(c.server_names) == ["example.com", "www.example.com"]


def test_extract_ssl_config_plain_server_yields_no_entry():
    ax = _TestContext()
    text = "http {\n  server {\n    listen 80;\n    server_name plain.example.com;\n  }\n}\n"
    result = extract_ssl_config(ax, NginxConfig(config=text))
    assert result.error == ""
    assert len(result.configs) == 0
