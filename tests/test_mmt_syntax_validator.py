from property_agent.knowledge import (
    load_property_example,
)

from property_agent.tools import (
    validate_mmt_syntax,
)


def test_verified_property_41():
    xml = load_property_example(
        "properties/41.SCTP_INIT_scan.xml"
    )

    result = validate_mmt_syntax(xml)

    assert result.valid is True


def test_verified_property_91():
    xml = load_property_example(
        "properties/91.malformed_ngap_pkt.xml"
    )

    result = validate_mmt_syntax(xml)

    assert result.valid is True


def test_verified_property_96():
    xml = load_property_example(
        "properties/96.http2_dos_recognition.xml"
    )

    result = validate_mmt_syntax(xml)

    assert result.valid is True


def test_security_property_type_is_valid():

    xml = """
    <beginning>

        <property
            value="COMPUTE"
            delay_min="0"
            delay_max="0"
            property_id="1"
            description="Security property"
            type_property="SECURITY">

            <event
                value="COMPUTE"
                event_id="1"
                description="Example event"
                boolean_expression="ngap.procedure_code == 4"/>

        </property>

    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is True


def test_security_rule_property_type_is_invalid():

    xml = """
    <beginning>

        <property
            value="COMPUTE"
            property_id="1"
            description="Invalid type"
            type_property="SECURITY_RULE">

            <event
                value="COMPUTE"
                event_id="1"
                description="Example"
                boolean_expression="ngap.procedure_code == 4"/>

        </property>

    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert "INVALID_PROPERTY_TYPE" in codes


def test_if_satisfied_is_valid():

    xml = """
    <beginning>

        <property
            value="COMPUTE"
            property_id="1"
            description="Reactive property"
            type_property="SECURITY"
            if_satisfied="em_action">

            <event
                value="COMPUTE"
                event_id="1"
                description="Example"
                boolean_expression="ngap.procedure_code == 4"/>

        </property>

    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is True


def test_if_violated_is_invalid():

    xml = """
    <beginning>

        <property
            value="COMPUTE"
            property_id="1"
            description="Invalid reactive attribute"
            type_property="SECURITY"
            if_violated="em_action">

            <event
                value="COMPUTE"
                event_id="1"
                description="Example"
                boolean_expression="ngap.procedure_code == 4"/>

        </property>

    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is False

    codes = {
        issue.code
        for issue in result.issues
    }

    assert (
        "INVALID_PROPERTY_ATTRIBUTE"
        in codes
    )


def test_delay_zero_plus_is_valid():

    xml = """
    <beginning>

        <property
            value="THEN"
            delay_units="ms"
            delay_min="0+"
            delay_max="10"
            property_id="1"
            description="Delay test"
            type_property="ATTACK">

            <event
                value="COMPUTE"
                event_id="1"
                description="First"
                boolean_expression="ngap.procedure_code == 4"/>

            <event
                value="COMPUTE"
                event_id="2"
                description="Second"
                boolean_expression="ngap.procedure_code == 46"/>

        </property>

    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is True

def test_rejects_ungrouped_compound_boolean_expression():
    xml = """
    <beginning>
        <property
            value="COMPUTE"
            property_id="1"
            description="Test"
            type_property="SECURITY">

            <event
                value="COMPUTE"
                event_id="1"
                description="Test"
                boolean_expression="(ngap.procedure_code == 4) &amp;&amp; (ngap.amf_ue_id == 1)"/>

        </property>
    </beginning>
    """

    result = validate_mmt_syntax(
        xml
    )

    assert result.valid is False

    assert any(
        issue.code
        == "COMPOUND_BOOLEAN_NOT_GROUPED"
        for issue in result.issues
    )

def test_accepts_grouped_compound_boolean_expression():
    xml = """
    <beginning>
        <property
            value="COMPUTE"
            property_id="1"
            description="Test"
            type_property="SECURITY">

            <event
                value="COMPUTE"
                event_id="1"
                description="Test"
                boolean_expression="((ngap.procedure_code == 4) &amp;&amp; (ngap.amf_ue_id == 1))"/>

        </property>
    </beginning>
    """

    result = validate_mmt_syntax(
        xml
    )

    assert result.valid is True

def test_accepts_nested_grouped_compound_boolean_expression():
    xml = """
    <beginning>
        <property
            value="COMPUTE"
            property_id="1"
            description="Test"
            type_property="SECURITY">

            <event
                value="COMPUTE"
                event_id="1"
                description="Test"
                boolean_expression="((((http2.header_method == 131) || (http2.header_method == 130)) || (http2.type == 8)) &amp;&amp; (ip.src != ip.dst))"/>

        </property>
    </beginning>
    """

    result = validate_mmt_syntax(
        xml
    )

    assert result.valid is True

def test_property_rejects_more_than_two_direct_children():
    xml = """
    <beginning>
        <property
            value="THEN"
            property_id="103"
            type_property="ATTACK">

            <event
                value="COMPUTE"
                event_id="1"
                boolean_expression="(ngap.procedure_code == 4)"/>

            <event
                value="COMPUTE"
                event_id="2"
                boolean_expression="(ngap.amf_ue_id == ngap.amf_ue_id.1)"/>

            <event
                value="COMPUTE"
                event_id="3"
                boolean_expression="(ngap.packet_count > 10)"/>

        </property>
    </beginning>
    """

    result = validate_mmt_syntax(xml)

    assert result.valid is False

    assert any(
        issue.code == "INVALID_PROPERTY_ARITY"
        for issue in result.issues
    )