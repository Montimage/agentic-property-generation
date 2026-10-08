from property_agent.models import (
    MonitoringTask,
    RetrievalConfig,
)

from property_agent.retrieval import (
    VerifiedExampleRetriever,
)


def test_retrieval_disabled_by_default():
    task = MonitoringTask(
        id="retrieval_disabled",
        property_id="501",
        description=(
            "Detect an SCTP INIT scan."
        ),
        protocols=["sctp", "ip"],
    )

    retriever = (
        VerifiedExampleRetriever()
    )

    result = retriever.retrieve(
        task
    )

    assert result.enabled is False
    assert result.examples == []


def test_retrieve_sctp_scan_example():
    task = MonitoringTask(
        id="sctp_scan_task",
        property_id="502",
        description=(
            "Detect repeated SCTP INIT "
            "attempts targeting different "
            "destination ports."
        ),
        protocols=[
            "sctp",
            "ip",
        ],
        requirements=[
            (
                "Correlate repeated attempts "
                "from the same source."
            )
        ],
    )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
            )
        )
    )

    result = retriever.retrieve(
        task
    )

    assert result.enabled is True

    assert len(
        result.examples
    ) >= 1

    assert (
        result.examples[0].property_id
        == "41"
    )

    assert (
        "sctp"
        in result.examples[
            0
        ].matched_protocols
    )


def test_retrieve_authentication_example():
    task = MonitoringTask(
        id="authentication_task",
        property_id="503",
        description=(
            "Detect a 5G UE authentication "
            "hijack involving an identifier "
            "mismatch."
        ),
        protocols=[
            "ngap",
            "nas_5g",
            "sctp_data",
        ],
        requirements=[
            (
                "Correlate the authentication "
                "events."
            )
        ],
    )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
            )
        )
    )

    result = retriever.retrieve(
        task
    )

    assert result.examples

    assert (
        result.examples[0].property_id
        == "91"
    )


def test_retrieve_http2_dos_example():
    task = MonitoringTask(
        id="http2_dos_task",
        property_id="504",
        description=(
            "Detect HTTP2 flooding by "
            "counting traffic within a "
            "time window and applying "
            "a threshold."
        ),
        protocols=[
            "http2",
            "ip",
            "meta",
        ],
    )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
            )
        )
    )

    result = retriever.retrieve(
        task
    )

    assert result.examples

    assert (
        result.examples[0].property_id
        == "96"
    )


def test_unrelated_scenario_can_return_zero_examples():
    task = MonitoringTask(
        id="unrelated_ngap_task",
        property_id="505",
        description=(
            "Detect registration signaling "
            "associated with a previously "
            "unseen mobility condition."
        ),
        protocols=[
            "ngap",
        ],
    )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
            )
        )
    )

    result = retriever.retrieve(
        task
    )

    assert result.enabled is True

    assert (
        len(result.examples)
        <= 2
    )


def test_retrieval_is_stable_for_same_task():
    task = MonitoringTask(
        id="stable_retrieval",
        property_id="506",
        description=(
            "Detect repeated SCTP INIT "
            "attempts on different ports."
        ),
        protocols=[
            "sctp",
            "ip",
        ],
    )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
            )
        )
    )

    first = retriever.retrieve(
        task
    )

    second = retriever.retrieve(
        task
    )

    assert first == second

def test_retriever_does_not_force_irrelevant_example():
    index = [
        {
            "property_id": "900",
            "file": "properties/example.xml",
            "validated": True,
            "property_type": "ATTACK",
            "description": (
                "Authentication identifier "
                "mismatch."
            ),
            "protocols": [
                "ngap",
            ],
            "tags": [
                "authentication",
                "identifier_mismatch",
            ],
            "constructs": [
                "event_correlation",
            ],
        }
    ]

    def fake_index_loader():
        return index

    def fake_property_loader(
        path: str,
    ):
        return (
            "<beginning>"
            "<property "
            'property_id="900" '
            'type_property="ATTACK" '
            'description="Example" />'
            "</beginning>"
        )

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
                k=2,
                min_score=0.55,
            ),
            index_loader=(
                fake_index_loader
            ),
            property_loader=(
                fake_property_loader
            ),
        )
    )

    task = MonitoringTask(
        id="unrelated_task",
        property_id="901",
        description=(
            "Observe registration mobility "
            "state transitions."
        ),
        protocols=[
            "ngap",
        ],
    )

    result = retriever.retrieve(
        task
    )

    assert (
        result.candidate_count
        == 1
    )

    assert (
        result.examples
        == []
    )

def test_unvalidated_example_is_not_retrieved():
    index = [
        {
            "property_id": "999",
            "file": "properties/unvalidated.xml",
            "validated": False,
            "property_type": "ATTACK",
            "description": (
                "SCTP INIT scan across "
                "different ports."
            ),
            "protocols": [
                "sctp",
                "ip",
            ],
            "tags": [
                "sctp",
                "scan",
                "init",
            ],
            "constructs": [
                "multiple_events",
            ],
        }
    ]

    retriever = (
        VerifiedExampleRetriever(
            config=RetrievalConfig(
                enabled=True,
            ),
            index_loader=lambda: index,
            property_loader=lambda path: (
                "<beginning></beginning>"
            ),
        )
    )

    task = MonitoringTask(
        id="validation_filter",
        property_id="1000",
        description=(
            "Detect an SCTP INIT scan."
        ),
        protocols=[
            "sctp",
            "ip",
        ],
    )

    result = retriever.retrieve(
        task
    )

    assert (
        result.candidate_count
        == 0
    )

    assert result.examples == []