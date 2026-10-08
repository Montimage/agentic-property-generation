from lxml import etree

from property_agent.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

# Only XML parsing is performed here

def validate_xml(xml: str) -> ValidationResult:
    """
    Validate whether the supplied content is well-formed XML.

    This validator does not check any MMT-specific rules.
    """

    if not isinstance(xml, str):
        return ValidationResult(
            validator="xml",
            valid=False,
            issues=[
                ValidationIssue(
                    code="XML_NOT_STRING",
                    message="The supplied XML content is not a string.",
                    severity=ValidationSeverity.ERROR,
                )
            ],
        )

    parser = etree.XMLParser(
        recover=False,
        remove_blank_text=False,
    )

    try:
        etree.fromstring(
            xml.encode("utf-8"),
            parser,
        )

    except etree.XMLSyntaxError as exc:
        issues = []

        if exc.error_log:
            for error in exc.error_log:
                issues.append(
                    ValidationIssue(
                        code="XML_SYNTAX_ERROR",
                        message=error.message,
                        severity=ValidationSeverity.ERROR,
                        line=error.line if error.line > 0 else None,
                        column=error.column if error.column > 0 else None,
                    )
                )
        else:
            issues.append(
                ValidationIssue(
                    code="XML_SYNTAX_ERROR",
                    message=str(exc),
                    severity=ValidationSeverity.ERROR,
                )
            )

        return ValidationResult(
            validator="xml",
            valid=False,
            issues=issues,
        )

    return ValidationResult(
        validator="xml",
        valid=True,
        issues=[],
    )