from gen.messages_pb2 import NginxConfig, ValidationResult, Issue
from gen.axiom_context import AxiomContext

from nodes.nginx_parse import resolve


def validate_structure(ax: AxiomContext, input: NginxConfig) -> ValidationResult:
    """Validate a config's basic structural correctness — balanced braces,
    every directive terminated by `;` or opening a block — and report
    every issue found with its line number, without needing any other
    extraction.
    """
    _directives, issues, valid, error = resolve(input)
    if error:
        return ValidationResult(
            valid=False, issues=[Issue(line=0, severity="error", message=error)]
        )
    return ValidationResult(valid=valid, issues=issues)
