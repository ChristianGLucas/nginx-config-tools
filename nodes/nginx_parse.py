"""Shared parsing/extraction helpers for every node in this package.

Wraps nginxinc/crossplane (Apache-2.0), the official NGINX, Inc. config
parser. crossplane's own `parse()` API takes a filename, not a text blob, so
`parse_text_to_directives` writes the caller's text to an ephemeral temp file
solely to satisfy that API and deletes it immediately after — it never reads
back a caller-controlled path, and `single=True` means crossplane never
opens, globs, or follows any `include` directive onto disk (an `include`
directive is reported like any other directive, with its raw path as an
arg — never resolved).

Bounds enforced before crossplane ever runs (so a pathological input fails
fast with a structured error rather than a slow parse or a stack overflow):
  - MAX_CONFIG_BYTES on the raw UTF-8 byte length of the input text.
  - MAX_NESTING_DEPTH on brace nesting, found with a single linear scan
    (quote/comment aware) that never recurses.
"""

import os
import re
import tempfile
from collections import Counter
from typing import List, Optional, Tuple

import crossplane

from gen import messages_pb2 as m

MAX_CONFIG_BYTES = 2_000_000  # 2 MB
MAX_NESTING_DEPTH = 64

_LOCATION_MODIFIERS = {"=", "~", "~*", "^~"}
UPSTREAM_METHOD_DIRECTIVES = {"least_conn", "ip_hash", "hash", "random"}
_VAR_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# crossplane's own error strings end with " in <the temp file's path>:<line>"
# — strip that suffix so the message is stable across calls (the path is a
# fresh random tempfile name every invocation) and never leaks a host path.
_TRAILING_FILE_REF_RE = re.compile(r"\s+in\s+\S+:\d+\s*$")


def _sanitize_error_message(message: str) -> str:
    return _TRAILING_FILE_REF_RE.sub("", message)


def _find_excess_nesting(text: str) -> bool:
    """Single linear, non-recursive scan for brace depth > MAX_NESTING_DEPTH.

    Quote-aware (nginx tokens may be '...'/"..." quoted, and braces inside a
    quoted string are not structural) and comment-aware (a `#` starts a
    line comment outside of a quote). Approximate relative to nginx's own
    escaping rules, but that's fine here: this function's only job is a
    conservative pre-check that stops a maliciously deep config before the
    real (recursive) parser ever sees it, not to be the parser itself.
    """
    depth = 0
    in_squote = False
    in_dquote = False
    in_comment = False
    escaped = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
            continue
        if escaped:
            escaped = False
            continue
        if ch == "\\" and (in_squote or in_dquote):
            escaped = True
            continue
        if in_squote:
            if ch == "'":
                in_squote = False
            continue
        if in_dquote:
            if ch == '"':
                in_dquote = False
            continue
        if ch == "#":
            in_comment = True
            continue
        if ch == "'":
            in_squote = True
            continue
        if ch == '"':
            in_dquote = True
            continue
        if ch == "{":
            depth += 1
            if depth > MAX_NESTING_DEPTH:
                return True
        elif ch == "}":
            depth = max(0, depth - 1)
    return False


def _stmt_to_directive(stmt: dict, context_path: List[str]) -> "m.Directive":
    is_block = "block" in stmt
    d = m.Directive(
        name=stmt.get("directive") or "",
        args=list(stmt.get("args") or []),
        line=stmt.get("line") or 0,
        context_path=list(context_path),
        is_block=is_block,
    )
    if is_block:
        child_ctx = context_path + [d.name]
        for child_stmt in stmt["block"]:
            d.children.append(_stmt_to_directive(child_stmt, child_ctx))
    return d


def parse_text_to_directives(
    text: str,
) -> Tuple[List["m.Directive"], List["m.Issue"], bool, str]:
    """Parse raw nginx config text. Returns (directives, issues, valid, error).

    `error` is set (and directives/issues empty) only when the whole input
    could not be processed at all (over the size/depth bound). Otherwise
    parsing is best-effort: structural problems come back as `issues` with
    line numbers, never an exception.
    """
    if text is None:
        text = ""
    byte_len = len(text.encode("utf-8", errors="replace"))
    if byte_len > MAX_CONFIG_BYTES:
        return [], [], False, (
            f"input exceeds the {MAX_CONFIG_BYTES}-byte limit "
            f"({byte_len} bytes given)"
        )
    if _find_excess_nesting(text):
        return [], [], False, (
            f"brace nesting exceeds the {MAX_NESTING_DEPTH}-level limit"
        )

    fd, path = tempfile.mkstemp(prefix="nginx-config-tools-", suffix=".conf")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        payload = crossplane.parse(
            path,
            single=True,       # never resolve/open/glob include targets
            comments=False,
            catch_errors=True,  # collect issues instead of raising
            check_ctx=False,    # don't reject directives in "wrong" blocks
            check_args=True,    # DO validate argument counts/terminators —
            # this is what catches a missing ";" before the next directive
            # or block (e.g. "listen 80\n  location / {") rather than
            # silently absorbing the next token(s) into the wrong
            # directive's args. Recognized-directive validation only:
            # analyze() skips this check entirely for any directive not in
            # crossplane's own DIRECTIVES table, so unrecognized/third-party
            # directives (lua_shared_dict, etc.) are still never rejected.
            strict=False,       # don't reject unrecognized directives
        )
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    file_result = payload["config"][0] if payload.get("config") else {}
    stmts = file_result.get("parsed") or []
    directives = [_stmt_to_directive(s, []) for s in stmts]

    issues: List["m.Issue"] = []
    for err in file_result.get("errors") or []:
        issues.append(
            m.Issue(
                line=err.get("line") or 0,
                severity="error",
                message=_sanitize_error_message(str(err.get("error") or "")),
            )
        )
    valid = len(issues) == 0
    return directives, issues, valid, ""


def resolve(
    config: "m.NginxConfig",
) -> Tuple[List["m.Directive"], List["m.Issue"], bool, str]:
    """Reuse an already-parsed NginxConfig, or parse its raw `config` text.

    Every node accepting NginxConfig calls this first: chaining after
    ParseConfig (directives already populated) skips re-parsing entirely;
    calling any node standalone with just `config` set parses on the fly.
    """
    if len(config.directives) > 0:
        return list(config.directives), list(config.issues), config.valid, config.error
    return parse_text_to_directives(config.config)


def flatten(directives: List["m.Directive"]):
    """Yield every directive in the tree, depth-first, in source order."""
    for d in directives:
        yield d
        if d.children:
            yield from flatten(d.children)


def parse_location_args(args: List[str]) -> Tuple[str, str]:
    if not args:
        return "", ""
    if args[0] in _LOCATION_MODIFIERS:
        return args[0], (args[1] if len(args) > 1 else "")
    return "", args[0]


def parse_listen_args(args: List[str]) -> Tuple[str, int, bool, bool, bool]:
    """Decompose a `listen` directive's args into (address, port, ssl, http2, default_server)."""
    flags = args[1:]
    ssl = "ssl" in flags
    http2 = "http2" in flags
    default_server = "default_server" in flags or "default" in flags
    address = ""
    port = 0
    if not args:
        return address, port, ssl, http2, default_server
    raw_addr = args[0]
    if raw_addr.startswith("unix:"):
        return raw_addr, 0, ssl, http2, default_server
    if raw_addr.startswith("["):
        close = raw_addr.find("]")
        if close != -1:
            address = raw_addr[: close + 1]
            rest = raw_addr[close + 1 :]
            if rest.startswith(":"):
                try:
                    port = int(rest[1:])
                except ValueError:
                    port = 0
        else:
            address = raw_addr
        return address, port, ssl, http2, default_server
    if ":" in raw_addr:
        host, _, port_str = raw_addr.rpartition(":")
        try:
            port = int(port_str)
            address = host
        except ValueError:
            address = raw_addr
            port = 0
        return address, port, ssl, http2, default_server
    try:
        port = int(raw_addr)
        address = ""
    except ValueError:
        address = raw_addr
        port = 0
    return address, port, ssl, http2, default_server


def collect_locations(directives: List["m.Directive"]) -> List["m.LocationBlock"]:
    """Every `location` block anywhere, each tagged with its nearest
    enclosing server's server_name values (found top-down, since a
    Directive's own context_path only carries ancestor block *names*, not
    server_name *values*)."""
    out: List["m.LocationBlock"] = []

    def _walk(nodes: List["m.Directive"], server_names: List[str]):
        for d in nodes:
            if d.name == "location" and d.is_block:
                modifier, path = parse_location_args(list(d.args))
                out.append(
                    m.LocationBlock(
                        modifier=modifier,
                        path=path,
                        line=d.line,
                        server_names=list(server_names),
                        directives=list(d.children),
                        context_path=list(d.context_path),
                    )
                )
            if d.is_block:
                next_names = server_names
                if d.name == "server":
                    names = []
                    for c in d.children:
                        if c.name == "server_name":
                            names.extend(c.args)
                    next_names = names
                _walk(list(d.children), next_names)

    _walk(directives, [])
    return out


def find_vars(args: List[str]) -> List[str]:
    out: List[str] = []
    for a in args:
        out.extend(_VAR_RE.findall(a))
    return out
