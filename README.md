# nginx-config-tools

Deterministic structural parsing and inspection of nginx configuration text for the
[Axiom](https://axiom.co) marketplace, published under the `christiangeorgelucas` handle.

Wraps [`nginxinc/crossplane`](https://github.com/nginxinc/crossplane) (Apache-2.0), the official
NGINX, Inc. config parser — pure Python, zero runtime dependencies of its own, the same
lexer/grammar nginx's own tooling (and `nginx -t`-adjacent tooling) uses.

Every node is a pure, stateless transform: the config is always supplied as text by the caller.
There is no nginx execution, no filesystem access beyond an ephemeral temp file used only to
satisfy crossplane's file-based API (written and deleted within the same call), no network, no
wall-clock, no randomness. `include` directives are reported by path as data — never opened,
globbed, or fetched. The platform owns size/resource limits, not this package; a malformed
config always yields a structured result with line numbers — never a crash.

## The envelope

Every node accepts `NginxConfig`: an input-only `config` (raw text) convenience field, plus the
canonical parsed fields (`directives`, `issues`, `valid`, `error`). Call `ParseConfig` once and
chain its output into any other node to skip re-parsing, or call any node standalone with just
`config` set — it parses on the fly if `directives` isn't already populated.

## Nodes

| Node | What it does |
|---|---|
| `ParseConfig` | Full structured directive/block tree: name, args, line, context_path, nested children |
| `ListDirectives` | Every directive (top-level and nested), flattened into one ordered list |
| `ExtractServerBlocks` | Every `server { }` block: listen specs, server_names, directives |
| `ExtractLocationBlocks` | Every `location { }` block anywhere: modifier, path, enclosing server_names |
| `ExtractUpstreams` | Every `upstream` block: members (address + params) and load-balancing method |
| `ExtractListenDirectives` | Every `listen` decomposed: address, port, ssl, http2, default_server |
| `ExtractServerNames` | Every `server_name` value — the virtual-host inventory |
| `ExtractProxyTargets` | Every `proxy_pass`/`fastcgi_pass` — the routing/backend map |
| `ExtractSSLConfig` | Per-server ssl_certificate/ssl_certificate_key/ssl_protocols/ssl_ciphers |
| `ExtractDocumentRoots` | Every `root`/`alias` directive |
| `ExtractRewrites` | Every `rewrite` and `return` directive |
| `ExtractIncludes` | Every `include` directive's path (reported, never fetched) |
| `ExtractLogPaths` | Every `access_log`/`error_log` directive |
| `ExtractVariables` | Every `set $var` declaration and every `$var` usage, anywhere in the config |
| `GetDirectiveValue` | Look up a directive by name, optionally scoped to an exact context_path |
| `SummarizeConfig` | Directive/block counts, max nesting depth, server_name inventory, issue counts |
| `ValidateStructure` | Balanced braces, terminated directives — issues with line numbers |

## License

MIT — see [LICENSE](./LICENSE). `crossplane` is Apache-2.0 (Copyright NGINX, Inc. and Arie van
Luttikhuizen) and has zero third-party runtime dependencies.

Built for the Axiom marketplace.
