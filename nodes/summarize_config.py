from collections import Counter

from gen.messages_pb2 import NginxConfig, ConfigSummary
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten


def summarize_config(ax: AxiomContext, input: NginxConfig) -> ConfigSummary:
    """Summarize a parsed config: total directive count, a block-type ->
    count map, server/location/upstream counts, the deepest block nesting
    level, the unique server_name inventory, and the count of parse
    errors/warnings.
    """
    directives, issues, _valid, error = resolve(input)
    if error:
        return ConfigSummary(error=error)

    flat = list(flatten(directives))
    block_counts = Counter(d.name for d in flat if d.is_block)
    server_names = set()
    for d in flat:
        if d.name == "server_name":
            server_names.update(d.args)
    max_depth = max((len(d.context_path) for d in flat), default=0)
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    return ConfigSummary(
        total_directives=len(flat),
        block_counts=dict(block_counts),
        server_count=block_counts.get("server", 0),
        location_count=block_counts.get("location", 0),
        upstream_count=block_counts.get("upstream", 0),
        max_depth=max_depth,
        server_names=sorted(server_names),
        error_count=error_count,
        warning_count=warning_count,
    )
