from gen.messages_pb2 import NginxConfig, LogPathList, LogPathEntry
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve, flatten

_LOG_DIRECTIVES = {"access_log", "error_log"}


def extract_log_paths(ax: AxiomContext, input: NginxConfig) -> LogPathList:
    """Extract every `access_log` and `error_log` directive: which one it
    was, the destination path (or "off"), and the format name / log level
    (2nd argument) if present.
    """
    directives, _issues, _valid, error = resolve(input)
    if error:
        return LogPathList(error=error)

    logs = []
    for d in flatten(directives):
        if d.name not in _LOG_DIRECTIVES:
            continue
        args = list(d.args)
        path = args[0] if len(args) > 0 else ""
        format_or_level = args[1] if len(args) > 1 else ""
        logs.append(
            LogPathEntry(
                directive=d.name,
                path=path,
                format_or_level=format_or_level,
                line=d.line,
                context_path=list(d.context_path),
            )
        )
    return LogPathList(logs=logs)
