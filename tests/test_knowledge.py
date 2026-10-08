import pytest

from property_agent.knowledge import (
    load_example_index,
    load_property_example,
    load_protocol_attributes,
    list_protocols_with_attribute_knowledge,
)


@pytest.mark.parametrize(
    "protocol, expected_id, expected_count, expected_attributes",
    [
        (
            "ngap",
            903,
            14,
            {
                "ngap.procedure_code",
                "ngap.amf_ue_id",
                "ngap.ran_ue_id",
            },
        ),
        (
            "nas_5g",
            904,
            16,
            {
                "nas_5g.protocol_discriminator",
                "nas_5g.message_type",
                "nas_5g.sequence_number",
            },
        ),
        (
            "sctp",
            304,
            17,
            {
                "sctp.src_port",
                "sctp.dest_port",
                "sctp.ch_type",
            },
        ),
        (
            "sctp_data",
            631,
            17,
            {
                "sctp_data.ch_type",
                "sctp_data.data_stream",
                "sctp_data.data_ppid",
            },
        ),
        (
            "ip",
            178,
            45,
            {
                "ip.src",
                "ip.dst",
                "ip.client_addr",
                "ip.server_addr",
                "ip.session_id",
            },
        ),
        (
            "http2",
            700,
            17,
            {
                "http2.type",
                "http2.header_method",
                "http2.header_stream_id",
                "http2.payload_data",
            },
        ),
        (
            "meta",
            1,
            20,
            {
                "meta.direction",
                "meta.utime",
                "meta.packet_len",
                "meta.packet_index",
            },
        ),
    ],
)
def test_load_protocol_attributes(
    protocol,
    expected_id,
    expected_count,
    expected_attributes,
):
    knowledge = load_protocol_attributes(protocol)

    assert knowledge["protocol_id"] == expected_id
    assert knowledge["protocol_name"] == protocol
    assert knowledge["source"] == "MMT protocol iterator"

    attributes = knowledge["attributes"]

    assert len(attributes) == expected_count

    qualified_names = {
        attribute["qualified_name"]
        for attribute in attributes
    }

    for expected_attribute in expected_attributes:
        assert expected_attribute in qualified_names


@pytest.mark.parametrize(
    "protocol",
    [
        "ngap",
        "nas_5g",
        "sctp",
        "sctp_data",
        "ip",
        "http2",
        "meta",
    ],
)
def test_protocol_attribute_structure(protocol):
    knowledge = load_protocol_attributes(protocol)

    attributes = knowledge["attributes"]

    assert len(attributes) > 0

    for attribute in attributes:
        assert "id" in attribute
        assert "name" in attribute
        assert "qualified_name" in attribute

        assert attribute["qualified_name"] == (
            f"{protocol}.{attribute['name']}"
        )


@pytest.mark.parametrize(
    "protocol",
    [
        "ngap",
        "nas_5g",
        "sctp",
        "sctp_data",
        "ip",
        "http2",
        "meta",
    ],
)
def test_protocol_attributes_are_unique(protocol):
    knowledge = load_protocol_attributes(protocol)

    attributes = knowledge["attributes"]

    ids = [
        attribute["id"]
        for attribute in attributes
    ]

    names = [
        attribute["name"]
        for attribute in attributes
    ]

    qualified_names = [
        attribute["qualified_name"]
        for attribute in attributes
    ]

    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))
    assert len(qualified_names) == len(
        set(qualified_names)
    )


def test_load_example_index():
    examples = load_example_index()

    assert isinstance(examples, list)
    assert len(examples) >= 3

    property_ids = {
        example["property_id"]
        for example in examples
    }

    assert "41" in property_ids
    assert "91" in property_ids
    assert "96" in property_ids

    assert all(
        example["validated"]
        for example in examples
    )


def test_load_property_41():
    examples = load_example_index()

    example = next(
        item
        for item in examples
        if item["property_id"] == "41"
    )

    xml = load_property_example(
        example["file"]
    )

    assert 'property_id="41"' in xml
    assert "<operator" in xml
    assert "sctp.ch_type" in xml
    assert "sctp.dest_port" in xml
    assert "ip.src" in xml
    assert "ip.dst" in xml


def test_load_property_91():
    examples = load_example_index()

    example = next(
        item
        for item in examples
        if item["property_id"] == "91"
    )

    xml = load_property_example(
        example["file"]
    )

    assert 'property_id="91"' in xml
    assert "ngap.procedure_code" in xml
    assert "nas_5g.message_type" in xml
    assert "sctp_data.data_stream" in xml


def test_load_property_96():
    examples = load_example_index()

    example = next(
        item
        for item in examples
        if item["property_id"] == "96"
    )

    xml = load_property_example(
        example["file"]
    )

    assert 'property_id="96"' in xml
    assert "embedded_functions" in xml
    assert "em_5g_check_msg_throughput" in xml
    assert "http2.header_method" in xml
    assert "meta.utime" in xml

def test_list_protocols_with_attribute_knowledge():
    protocols = (
        list_protocols_with_attribute_knowledge()
    )

    assert "ngap" in protocols
    assert "nas_5g" in protocols
    assert "sctp" in protocols
    assert "http2" in protocols