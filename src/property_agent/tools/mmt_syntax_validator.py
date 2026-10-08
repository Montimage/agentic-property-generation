import re
from collections import Counter

from lxml import etree

from property_agent.models import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class MMTSyntaxValidator:
    """
    Deterministic validator for the known structural and syntactic
    rules of MMT event-based monitoring properties.

    This validator does not determine semantic correctness and does
    not validate whether protocol attributes are exposed by MMT.

    Some structural rules are derived from behavior confirmed with
    the real MMT compile_rule parser.
    """

    VALID_ATTRIBUTES = {
        "property": {
            "value",
            "delay_min",
            "delay_max",
            "property_id",
            "description",
            "type_property",
            "if_satisfied",
            "delay_units",
        },
        "operator": {
            "value",
            "delay_units",
            "delay_min",
            "delay_max",
        },
        "event": {
            "value",
            "event_id",
            "description",
            "boolean_expression",
        },
    }

    REQUIRED_ATTRIBUTES = {
        "property": {
            "property_id",
            "description",
            "type_property",
        },
        "event": {
            "value",
            "event_id",
            "description",
            "boolean_expression",
        },
    }

    ALLOWED_CHILDREN = {
        "beginning": {
            "property",
            "embedded_functions",
        },
        "property": {
            "event",
            "operator",
        },
        "operator": {
            "event",
        },
    }

    VALID_PROPERTY_TYPES = {
        "ATTACK",
        "SECURITY",
        "EVASION",
        "TEST",
    }

    VALID_PROPERTY_VALUES = {
        "THEN",
        "COMPUTE",
    }

    VALID_OPERATOR_VALUES = {
        "THEN",
        "COMPUTE",
    }

    VALID_EVENT_VALUES = {
        "COMPUTE",
    }

    # Confirmed by the real MMT compile_rule parser:
    #
    # HALT_SEC: Error 13f:
    # Unexpected more than 2 children in property tag
    #
    MAX_PROPERTY_CHILDREN = 2

    # Verified/legacy examples include:
    #
    # 0
    # 10
    # -1
    # 0+
    # 5+
    # -3+
    #
    DELAY_PATTERN = re.compile(r"-?\d+\+?")

    def validate_delay(
        self,
        value: str,
    ) -> bool:
        return (
            self.DELAY_PATTERN.fullmatch(
                value
            )
            is not None
        )

    @staticmethod
    def _issue(
        code: str,
        message: str,
        element=None,
        context=None,
    ) -> ValidationIssue:

        line = (
            getattr(
                element,
                "sourceline",
                None,
            )
            if element is not None
            else None
        )

        return ValidationIssue(
            code=code,
            message=message,
            severity=(
                ValidationSeverity.ERROR
            ),
            line=line,
            context=context or {},
        )

    @staticmethod
    def _element_children(
        element,
    ):
        """
        Return actual XML child elements while ignoring
        comments.
        """

        return [
            child
            for child in element
            if not isinstance(
                child,
                etree._Comment,
            )
        ]

    def _validate_allowed_children(
        self,
        element,
    ) -> list[ValidationIssue]:

        issues = []

        allowed = (
            self.ALLOWED_CHILDREN.get(
                element.tag
            )
        )

        if allowed is None:
            return issues

        for child in self._element_children(
            element
        ):
            if child.tag not in allowed:
                issues.append(
                    self._issue(
                        code=(
                            "INVALID_CHILD_TAG"
                        ),
                        message=(
                            f"Tag '{child.tag}' is "
                            f"not allowed inside "
                            f"'{element.tag}'."
                        ),
                        element=child,
                        context={
                            "parent":
                                element.tag,
                            "child":
                                child.tag,
                        },
                    )
                )

        return issues

    def _validate_property_child_count(
        self,
        prop,
    ) -> list[ValidationIssue]:
        """
        Validate the direct-child arity of an MMT
        property.

        The real MMT compile_rule parser rejects a
        property containing more than two direct child
        elements.

        This check intentionally counts direct XML child
        elements only. Descendant events contained inside
        another valid construct are not counted here.
        """

        issues = []

        children = (
            self._element_children(
                prop
            )
        )

        child_count = len(
            children
        )

        if (
            child_count
            > self.MAX_PROPERTY_CHILDREN
        ):
            issues.append(
                self._issue(
                    code=(
                        "INVALID_PROPERTY_ARITY"
                    ),
                    message=(
                        "An MMT property may contain "
                        "at most "
                        f"{self.MAX_PROPERTY_CHILDREN} "
                        "direct child elements; "
                        f"found {child_count}."
                    ),
                    element=prop,
                    context={
                        "child_count":
                            child_count,
                        "max_children":
                            (
                                self
                                .MAX_PROPERTY_CHILDREN
                            ),
                        "child_tags": [
                            child.tag
                            for child in children
                        ],
                    },
                )
            )

        return issues

    def _validate_delay_attributes(
        self,
        element,
        element_name: str,
    ) -> list[ValidationIssue]:

        issues = []

        for attribute in (
            "delay_min",
            "delay_max",
        ):
            value = element.get(
                attribute
            )

            if (
                value is not None
                and not self.validate_delay(
                    value
                )
            ):
                issues.append(
                    self._issue(
                        code="INVALID_DELAY",
                        message=(
                            f"Invalid {attribute} "
                            f"value '{value}' in "
                            f"{element_name}."
                        ),
                        element=element,
                        context={
                            "element":
                                element_name,
                            "attribute":
                                attribute,
                            "value":
                                value,
                        },
                    )
                )

        return issues

    def _validate_property_attributes(
        self,
        prop,
    ) -> list[ValidationIssue]:

        issues = []

        for attribute in prop.attrib:
            if (
                attribute
                not in (
                    self
                    .VALID_ATTRIBUTES[
                        "property"
                    ]
                )
            ):
                issues.append(
                    self._issue(
                        code=(
                            "INVALID_PROPERTY_"
                            "ATTRIBUTE"
                        ),
                        message=(
                            f"Attribute "
                            f"'{attribute}' is not "
                            "supported in a "
                            "property."
                        ),
                        element=prop,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        for attribute in (
            self.REQUIRED_ATTRIBUTES[
                "property"
            ]
        ):
            if (
                attribute
                not in prop.attrib
            ):
                issues.append(
                    self._issue(
                        code=(
                            "MISSING_PROPERTY_"
                            "ATTRIBUTE"
                        ),
                        message=(
                            "Property is missing "
                            "required attribute "
                            f"'{attribute}'."
                        ),
                        element=prop,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        property_type = prop.get(
            "type_property"
        )

        if (
            property_type is not None
            and property_type
            not in self.VALID_PROPERTY_TYPES
        ):
            issues.append(
                self._issue(
                    code=(
                        "INVALID_PROPERTY_TYPE"
                    ),
                    message=(
                        "Unsupported property "
                        f"type '{property_type}'."
                    ),
                    element=prop,
                    context={
                        "type_property":
                            property_type
                    },
                )
            )

        value = prop.get(
            "value"
        )

        if (
            value is not None
            and value
            not in self.VALID_PROPERTY_VALUES
        ):
            issues.append(
                self._issue(
                    code=(
                        "INVALID_PROPERTY_VALUE"
                    ),
                    message=(
                        "Unsupported property "
                        f"value '{value}'."
                    ),
                    element=prop,
                    context={
                        "value":
                            value
                    },
                )
            )

        issues.extend(
            self._validate_delay_attributes(
                prop,
                "property",
            )
        )

        return issues

    def _validate_operator_attributes(
        self,
        operator,
    ) -> list[ValidationIssue]:

        issues = []

        for attribute in operator.attrib:
            if (
                attribute
                not in (
                    self
                    .VALID_ATTRIBUTES[
                        "operator"
                    ]
                )
            ):
                issues.append(
                    self._issue(
                        code=(
                            "INVALID_OPERATOR_"
                            "ATTRIBUTE"
                        ),
                        message=(
                            f"Attribute "
                            f"'{attribute}' is not "
                            "supported in an "
                            "operator."
                        ),
                        element=operator,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        value = operator.get(
            "value"
        )

        if (
            value is not None
            and value
            not in self.VALID_OPERATOR_VALUES
        ):
            issues.append(
                self._issue(
                    code=(
                        "INVALID_OPERATOR_VALUE"
                    ),
                    message=(
                        "Unsupported operator "
                        f"value '{value}'. "
                        "Supported values are: "
                        f"{', '.join(sorted(self.VALID_OPERATOR_VALUES))}."
                    ),
                    element=operator,
                    context={
                        "value":
                            value,
                        "allowed_values":
                            sorted(
                                self
                                .VALID_OPERATOR_VALUES
                            ),
                    },
                )
            )

        issues.extend(
            self._validate_delay_attributes(
                operator,
                "operator",
            )
        )

        return issues

    def _validate_event(
        self,
        event,
    ) -> list[ValidationIssue]:

        issues = []

        # Events are leaf nodes.
        if self._element_children(
            event
        ):
            issues.append(
                self._issue(
                    code=(
                        "EVENT_HAS_CHILDREN"
                    ),
                    message=(
                        "An event must be a "
                        "leaf node and cannot "
                        "contain child "
                        "elements."
                    ),
                    element=event,
                )
            )

        for attribute in event.attrib:
            if (
                attribute
                not in (
                    self
                    .VALID_ATTRIBUTES[
                        "event"
                    ]
                )
            ):
                issues.append(
                    self._issue(
                        code=(
                            "INVALID_EVENT_"
                            "ATTRIBUTE"
                        ),
                        message=(
                            f"Attribute "
                            f"'{attribute}' is not "
                            "supported in an "
                            "event."
                        ),
                        element=event,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        for attribute in (
            self.REQUIRED_ATTRIBUTES[
                "event"
            ]
        ):
            if (
                attribute
                not in event.attrib
            ):
                issues.append(
                    self._issue(
                        code=(
                            "MISSING_EVENT_"
                            "ATTRIBUTE"
                        ),
                        message=(
                            "Event is missing "
                            "required attribute "
                            f"'{attribute}'."
                        ),
                        element=event,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        value = event.get(
            "value"
        )

        if (
            value is not None
            and value
            not in self.VALID_EVENT_VALUES
        ):
            issues.append(
                self._issue(
                    code=(
                        "INVALID_EVENT_VALUE"
                    ),
                    message=(
                        "Unsupported event value "
                        f"'{value}'."
                    ),
                    element=event,
                    context={
                        "value":
                            value
                    },
                )
            )

        issues.extend(
            self._validate_boolean_expression(
                event
            )
        )

        return issues

    def _validate_compute_constraints(
        self,
        element,
        element_name: str,
    ) -> list[ValidationIssue]:
        """
        The available MMT format states that COMPUTE
        requires one event and zero delays.
        """

        issues = []

        effective_value = (
            element.get(
                "value",
                "COMPUTE",
            )
        )

        if (
            effective_value
            != "COMPUTE"
        ):
            return issues

        events = element.xpath(
            ".//event"
        )

        if len(events) != 1:
            issues.append(
                self._issue(
                    code=(
                        "INVALID_COMPUTE_"
                        "EVENT_COUNT"
                    ),
                    message=(
                        f"A COMPUTE "
                        f"{element_name} must "
                        "contain exactly one "
                        "event; found "
                        f"{len(events)}."
                    ),
                    element=element,
                    context={
                        "event_count":
                            len(events)
                    },
                )
            )

        for attribute in (
            "delay_min",
            "delay_max",
        ):
            value = element.get(
                attribute
            )

            if (
                value is not None
                and value != "0"
            ):
                issues.append(
                    self._issue(
                        code=(
                            "INVALID_COMPUTE_DELAY"
                        ),
                        message=(
                            f"A COMPUTE "
                            f"{element_name} "
                            f"must use "
                            f"{attribute}=0 "
                            "when explicitly "
                            "specified."
                        ),
                        element=element,
                        context={
                            "attribute":
                                attribute,
                            "value":
                                value,
                        },
                    )
                )

        return issues

    def _validate_unique_property_ids(
        self,
        root,
    ) -> list[ValidationIssue]:

        issues = []

        ids = [
            prop.get(
                "property_id"
            )
            for prop in root.findall(
                "property"
            )
            if prop.get(
                "property_id"
            )
        ]

        counts = Counter(
            ids
        )

        for (
            property_id,
            count,
        ) in counts.items():

            if count > 1:
                issues.append(
                    self._issue(
                        code=(
                            "DUPLICATE_PROPERTY_ID"
                        ),
                        message=(
                            f"Property id "
                            f"'{property_id}' "
                            f"occurs {count} "
                            "times."
                        ),
                        context={
                            "property_id":
                                property_id,
                            "count":
                                count,
                        },
                    )
                )

        return issues

    def _validate_unique_event_ids(
        self,
        prop,
    ) -> list[ValidationIssue]:
        """
        Event identifiers are scoped to the complete
        property, including events contained in different
        operators.
        """

        issues = []

        ids = [
            event.get(
                "event_id"
            )
            for event in prop.xpath(
                ".//event"
            )
            if event.get(
                "event_id"
            )
        ]

        counts = Counter(
            ids
        )

        for (
            event_id,
            count,
        ) in counts.items():

            if count > 1:
                issues.append(
                    self._issue(
                        code=(
                            "DUPLICATE_EVENT_ID"
                        ),
                        message=(
                            f"Event id "
                            f"'{event_id}' "
                            f"occurs {count} "
                            "times inside "
                            "property "
                            f"'{prop.get('property_id')}'."
                        ),
                        element=prop,
                        context={
                            "event_id":
                                event_id,
                            "count":
                                count,
                        },
                    )
                )

        return issues

    def _validate_embedded_functions(
        self,
        root,
    ) -> list[ValidationIssue]:

        issues = []

        for node in root.findall(
            "embedded_functions"
        ):
            if node.attrib:
                issues.append(
                    self._issue(
                        code=(
                            "EMBEDDED_FUNCTIONS_"
                            "HAS_ATTRIBUTES"
                        ),
                        message=(
                            "'embedded_functions' "
                            "should not contain XML "
                            "attributes."
                        ),
                        element=node,
                    )
                )

            if self._element_children(
                node
            ):
                issues.append(
                    self._issue(
                        code=(
                            "EMBEDDED_FUNCTIONS_"
                            "HAS_CHILD_ELEMENTS"
                        ),
                        message=(
                            "'embedded_functions' "
                            "should contain C code "
                            "as text/CDATA, not XML "
                            "child elements."
                        ),
                        element=node,
                    )
                )

        return issues

    @staticmethod
    def _is_fully_parenthesized(
        expression: str,
    ) -> bool:
        """
        Return True when the complete expression is
        enclosed by one outer pair of balanced
        parentheses.

        Examples:

            ((a == 1) && (b == 2))
                -> True

            ((((a == 1) || (b == 2)) || (c == 3))
                && (d != 4))
                -> True

            (a == 1) && (b == 2)
                -> False
        """

        expression = (
            expression.strip()
        )

        if (
            len(expression) < 2
            or expression[0] != "("
            or expression[-1] != ")"
        ):
            return False

        depth = 0

        for (
            index,
            character,
        ) in enumerate(
            expression
        ):
            if character == "(":
                depth += 1

            elif character == ")":
                depth -= 1

                if depth < 0:
                    return False

                if (
                    depth == 0
                    and index
                    != (
                        len(expression)
                        - 1
                    )
                ):
                    return False

        return depth == 0

    def _validate_boolean_expression(
        self,
        event,
    ) -> list[ValidationIssue]:
        """
        Validate known MMT boolean-expression grouping
        rules.

        When logical operators are used, the complete
        compound expression must be enclosed by one outer
        pair of balanced parentheses.

        This rule is based on behavior confirmed with the
        real MMT compile_rule parser.
        """

        issues = []

        expression = event.get(
            "boolean_expression"
        )

        if not expression:
            return issues

        expression = (
            expression.strip()
        )

        has_logical_operator = (
            "&&" in expression
            or "||" in expression
        )

        if (
            has_logical_operator
            and not (
                self
                ._is_fully_parenthesized(
                    expression
                )
            )
        ):
            issues.append(
                self._issue(
                    code=(
                        "COMPOUND_BOOLEAN_"
                        "NOT_GROUPED"
                    ),
                    message=(
                        "A compound "
                        "boolean_expression "
                        "must enclose the "
                        "complete logical "
                        "expression in an outer "
                        "pair of balanced "
                        "parentheses."
                    ),
                    element=event,
                    context={
                        "boolean_expression":
                            expression,
                    },
                )
            )

        return issues

    def validate(
        self,
        xml: str,
    ) -> ValidationResult:

        if not isinstance(
            xml,
            str,
        ):
            return ValidationResult(
                validator="mmt_syntax",
                valid=False,
                issues=[
                    ValidationIssue(
                        code=(
                            "XML_NOT_STRING"
                        ),
                        message=(
                            "The supplied XML "
                            "content is not a "
                            "string."
                        ),
                        severity=(
                            ValidationSeverity
                            .ERROR
                        ),
                    )
                ],
            )

        parser = etree.XMLParser(
            recover=False,
            remove_blank_text=False,
        )

        try:
            root = etree.fromstring(
                xml.encode(
                    "utf-8"
                ),
                parser,
            )

        except etree.XMLSyntaxError as exc:
            issues = []

            for error in exc.error_log:
                issues.append(
                    ValidationIssue(
                        code=(
                            "XML_SYNTAX_ERROR"
                        ),
                        message=(
                            error.message
                        ),
                        severity=(
                            ValidationSeverity
                            .ERROR
                        ),
                        line=(
                            error.line
                            if error.line > 0
                            else None
                        ),
                        column=(
                            error.column
                            if error.column > 0
                            else None
                        ),
                    )
                )

            if not issues:
                issues.append(
                    ValidationIssue(
                        code=(
                            "XML_SYNTAX_ERROR"
                        ),
                        message=str(
                            exc
                        ),
                        severity=(
                            ValidationSeverity
                            .ERROR
                        ),
                    )
                )

            return ValidationResult(
                validator="mmt_syntax",
                valid=False,
                issues=issues,
            )

        issues = []

        if root.tag != "beginning":
            issues.append(
                self._issue(
                    code="INVALID_ROOT",
                    message=(
                        "The root element "
                        "must be "
                        "'beginning'."
                    ),
                    element=root,
                    context={
                        "actual_root":
                            root.tag
                    },
                )
            )

            return ValidationResult(
                validator="mmt_syntax",
                valid=False,
                issues=issues,
            )

        if root.attrib:
            for attribute in root.attrib:
                issues.append(
                    self._issue(
                        code=(
                            "BEGINNING_HAS_ATTRIBUTE"
                        ),
                        message=(
                            "The 'beginning' "
                            "element must not "
                            "have attribute "
                            f"'{attribute}'."
                        ),
                        element=root,
                        context={
                            "attribute":
                                attribute
                        },
                    )
                )

        issues.extend(
            self._validate_allowed_children(
                root
            )
        )

        properties = root.findall(
            "property"
        )

        if not properties:
            issues.append(
                self._issue(
                    code="NO_PROPERTY",
                    message=(
                        "The document must "
                        "contain at least one "
                        "property."
                    ),
                    element=root,
                )
            )

        issues.extend(
            self._validate_unique_property_ids(
                root
            )
        )

        issues.extend(
            self._validate_embedded_functions(
                root
            )
        )

        for prop in properties:

            issues.extend(
                self._validate_property_attributes(
                    prop
                )
            )

            issues.extend(
                self._validate_allowed_children(
                    prop
                )
            )

            # Compiler-confirmed direct-child arity rule.
            issues.extend(
                self._validate_property_child_count(
                    prop
                )
            )

            all_events = prop.xpath(
                ".//event"
            )

            if not all_events:
                issues.append(
                    self._issue(
                        code=(
                            "PROPERTY_HAS_NO_EVENT"
                        ),
                        message=(
                            "A property must "
                            "contain at least "
                            "one event."
                        ),
                        element=prop,
                    )
                )

            issues.extend(
                self._validate_unique_event_ids(
                    prop
                )
            )

            issues.extend(
                self._validate_compute_constraints(
                    prop,
                    "property",
                )
            )

            for child in (
                self._element_children(
                    prop
                )
            ):

                if (
                    child.tag
                    == "event"
                ):
                    issues.extend(
                        self._validate_event(
                            child
                        )
                    )

                elif (
                    child.tag
                    == "operator"
                ):

                    issues.extend(
                        self._validate_operator_attributes(
                            child
                        )
                    )

                    issues.extend(
                        self._validate_allowed_children(
                            child
                        )
                    )

                    operator_events = (
                        child.findall(
                            "event"
                        )
                    )

                    if not operator_events:
                        issues.append(
                            self._issue(
                                code=(
                                    "OPERATOR_HAS_NO_EVENT"
                                ),
                                message=(
                                    "An operator "
                                    "must contain "
                                    "at least one "
                                    "event."
                                ),
                                element=child,
                            )
                        )

                    issues.extend(
                        self._validate_compute_constraints(
                            child,
                            "operator",
                        )
                    )

                    for event in (
                        operator_events
                    ):
                        issues.extend(
                            self._validate_event(
                                event
                            )
                        )

        has_errors = any(
            issue.severity
            == ValidationSeverity.ERROR
            for issue in issues
        )

        return ValidationResult(
            validator="mmt_syntax",
            valid=not has_errors,
            issues=issues,
        )


def validate_mmt_syntax(
    xml: str,
) -> ValidationResult:
    """
    Convenience entry point for future tool invocation.
    """

    return (
        MMTSyntaxValidator()
        .validate(xml)
    )