from gen.messages_pb2 import NginxConfig, LocationBlockList
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, collect_locations


def extract_location_blocks(ax: AxiomContext, input: NginxConfig) -> LocationBlockList:
    """Extract every `location { ... }` block anywhere in the config: its
    match modifier ("", "=", "~", "~*", "^~"), its path/pattern, the
    enclosing server's server_name values (for orientation), and its
    immediate directives.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return LocationBlockList(error=error)
    return LocationBlockList(locations=collect_locations(directives))
