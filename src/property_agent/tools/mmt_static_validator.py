import re

from lxml import etree

from property_agent.knowledge import (
    has_protocol_knowledge,
    load_protocol_attributes,
)

from property_agent.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

# This tools checks things that depend on references and external MMT knwowledge. The three checks are: protocol attributes, event references and embedded function calls. The XML parsing is done in a separate validator.

ATTRIBUTE_PATTERN = re.compile(
    r"\b"
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"\."
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\.([A-Za-z0-9_-]+))?"
    r"\b"
)


EMBEDDED_FUNCTION_CALL_PATTERN = re.compile(
    r"#([A-Za-z_][A-Za-z0-9_]*)\s*\("
)

def extract_referenced_protocols(
    xml: str,
) -> set[str]:
    """
    Return protocol namespaces referenced by event
    boolean expressions in an MMT property.

    This performs reference discovery only. It does not
    validate whether the protocols or attributes exist.
    """

    try:
        root = etree.fromstring(
            xml.encode("utf-8")
        )
    except etree.XMLSyntaxError:
        return set()

    protocols: set[str] = set()

    for event in root.xpath(".//event"):
        expression = event.get(
            "boolean_expression",
            "",
        )

        for match in ATTRIBUTE_PATTERN.finditer(
            expression
        ):
            protocols.add(
                match.group(1).lower()
            )

    return protocols

def _validate_event_references(
    root,
) -> list[ValidationIssue]:
    """
    Event identifiers are resolved across the entire
    property, not within individual operators.

    Verified property 41 demonstrates references from
    events in one operator to events contained in a
    previous sibling operator.
    """

    issues = []

    for prop in root.findall("property"):

        events = prop.xpath(".//event")

        available_ids = {
            event.get("event_id")
            for event in events
            if event.get("event_id")
        }

        for event in events:

            expression = event.get(
                "boolean_expression",
                "",
            )

            for match in (
                ATTRIBUTE_PATTERN.finditer(
                    expression
                )
            ):

                referenced_event = (
                    match.group(3)
                )

                if (
                    referenced_event is not None
                    and referenced_event
                    not in available_ids
                ):
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_EVENT_REFERENCE",
                            message=(
                                f"Reference "
                                f"'{match.group(0)}' uses "
                                f"event id "
                                f"'{referenced_event}', "
                                f"but no such event exists "
                                f"in property "
                                f"'{prop.get('property_id')}'."
                            ),
                            severity=ValidationSeverity.ERROR,
                            line=event.sourceline,
                            context={
                                "reference": match.group(0),
                                "event_id": referenced_event,
                                "property_id": prop.get(
                                    "property_id"
                                ),
                            },
                        )
                    )

    return issues


def _validate_protocol_attributes(
    root,
) -> list[ValidationIssue]:

    issues = []

    knowledge_cache = {}
    warned_protocols = set()

    for event in root.xpath(".//event"):

        expression = event.get(
            "boolean_expression",
            "",
        )

        for match in (
            ATTRIBUTE_PATTERN.finditer(
                expression
            )
        ):

            protocol = match.group(1)
            attribute = match.group(2)

            if not has_protocol_knowledge(
                protocol
            ):

                if (
                    protocol
                    not in warned_protocols
                ):
                    issues.append(
                        ValidationIssue(
                            code=(
                                "PROTOCOL_KNOWLEDGE_MISSING"
                            ),
                            message=(
                                f"No local MMT attribute "
                                f"knowledge is currently "
                                f"available for protocol "
                                f"'{protocol}'. Its "
                                f"attributes could not "
                                f"be verified."
                            ),
                            severity=(
                                ValidationSeverity.WARNING
                            ),
                            line=event.sourceline,
                            context={
                                "protocol": protocol
                            },
                        )
                    )

                    warned_protocols.add(
                        protocol
                    )

                continue

            if protocol not in knowledge_cache:

                data = load_protocol_attributes(
                    protocol
                )

                knowledge_cache[protocol] = {
                    item["name"]
                    for item in data["attributes"]
                }

            supported = (
                knowledge_cache[protocol]
            )

            if attribute not in supported:
                issues.append(
                    ValidationIssue(
                        code=(
                            "UNSUPPORTED_PROTOCOL_ATTRIBUTE"
                        ),
                        message=(
                            f"Attribute "
                            f"'{protocol}.{attribute}' "
                            f"is not exposed by the "
                            f"available MMT protocol "
                            f"knowledge."
                        ),
                        severity=(
                            ValidationSeverity.ERROR
                        ),
                        line=event.sourceline,
                        context={
                            "protocol": protocol,
                            "attribute": attribute,
                        },
                    )
                )

    return issues


def _validate_embedded_function_calls(
    root,
) -> list[ValidationIssue]:

    issues = []

    embedded_code = "\n".join(
        node.text or ""
        for node in root.findall(
            "embedded_functions"
        )
    )

    for event in root.xpath(".//event"):

        expression = event.get(
            "boolean_expression",
            "",
        )

        calls = (
            EMBEDDED_FUNCTION_CALL_PATTERN
            .findall(expression)
        )

        for function_name in calls:

            # At this stage we can only resolve
            # custom em_* functions defined locally.
            if not function_name.startswith(
                "em_"
            ):
                continue

            definition_pattern = re.compile(
                rf"\b"
                rf"{re.escape(function_name)}"
                rf"\s*\("
            )

            if not definition_pattern.search(
                embedded_code
            ):
                issues.append(
                    ValidationIssue(
                        code=(
                            "UNDEFINED_EMBEDDED_FUNCTION"
                        ),
                        message=(
                            f"Custom embedded function "
                            f"'{function_name}' is "
                            f"called by an event but "
                            f"no definition was found "
                            f"in embedded_functions."
                        ),
                        severity=(
                            ValidationSeverity.ERROR
                        ),
                        line=event.sourceline,
                        context={
                            "function": function_name
                        },
                    )
                )

    return issues


def validate_mmt_static(
    xml: str,
) -> ValidationResult:

    try:
        root = etree.fromstring(
            xml.encode("utf-8")
        )

    except etree.XMLSyntaxError as exc:
        return ValidationResult(
            validator="mmt_static",
            valid=False,
            issues=[
                ValidationIssue(
                    code="XML_SYNTAX_ERROR",
                    message=str(exc),
                    severity=ValidationSeverity.ERROR,
                    line=exc.lineno,
                )
            ],
        )

    issues = []

    issues.extend(
        _validate_event_references(
            root
        )
    )

    issues.extend(
        _validate_protocol_attributes(
            root
        )
    )

    issues.extend(
        _validate_embedded_function_calls(
            root
        )
    )

    has_errors = any(
        issue.severity
        == ValidationSeverity.ERROR
        for issue in issues
    )

    return ValidationResult(
        validator="mmt_static",
        valid=not has_errors,
        issues=issues,
    )