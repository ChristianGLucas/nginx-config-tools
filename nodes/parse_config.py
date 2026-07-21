from gen.messages_pb2 import NginxConfig
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve


def parse_config(ax: AxiomContext, input: NginxConfig) -> NginxConfig:
    """Parse nginx config text into its full structured directive/block
    tree: every directive's name, arguments, 1-based line number,
    context_path (enclosing block names, outermost first), and nested
    children for blocks (server, location, upstream, http, if, ...).
    Structural problems (unbalanced braces, an unterminated directive) come
    back as `issues` with line numbers instead of raising. Every other node
    in this package accepts the same NginxConfig envelope and re-parses
    `config` itself if `directives` isn't already populated — so calling
    this first is optional, but chaining its output into another node in
    this package avoids re-parsing the same text twice.
    """
    directives, issues, valid, error = resolve(input)
    return NginxConfig(directives=directives, issues=issues, valid=valid, error=error)
