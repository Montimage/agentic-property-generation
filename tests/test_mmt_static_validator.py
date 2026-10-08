from property_agent.knowledge import (
    load_property_example,
)

from property_agent.tools import (
    validate_mmt_static,
)


def test_property_41_cross_operator_references_exist():

    xml = load_property_example(
        "properties/41.SCTP_INIT_scan.xml"
    )

    result = validate_mmt_static(xml)

    reference_errors = [
        issue
        for issue in result.issues
        if issue.code
        == "UNKNOWN_EVENT_REFERENCE"
    ]

    assert len(reference_errors) == 0