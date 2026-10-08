from property_agent.models import (
    GeneratedProperty,
    MonitoringTask,
    SemanticAssessment,
)

from property_agent.semantic import (
    SemanticAssessmentGuard,
)


def make_task() -> MonitoringTask:
    return MonitoringTask(
        id="guard_test_001",
        property_id="201",
        description=(
            "Detect repeated NGAP observations "
            "for the same AMF UE identifier."
        ),
        protocols=[
            "ngap",
        ],
        monitoring_point="AMF",
        requirements=[
            (
                "detect when more than 10 NGAP "
                "observations have been seen for the "
                "same ngap.amf_ue_id"
            ),
            (
                "treat observations with the same "
                "ngap.amf_ue_id as belonging to the "
                "same monitored entity"
            ),
        ],
        ambiguities=[],
        assumptions=[],
    )


def make_embedded_property() -> GeneratedProperty:
    return GeneratedProperty(
        task_id="guard_test_001",
        model="test",
        attempt=2,
        xml="""
<beginning>
    <embedded_functions><![CDATA[
static inline bool em_check_ngap_count(
    const void *data
) {
    return true;
}
]]></embedded_functions>

    <property
        value="COMPUTE"
        property_id="201"
        type_property="ATTACK"
        description="test">

        <event
            value="COMPUTE"
            event_id="1"
            description="test"
            boolean_expression="(#em_check_ngap_count(ngap.amf_ue_id) == true)"/>

    </property>
</beginning>
""".strip(),
    )


def make_plain_property() -> GeneratedProperty:
    return GeneratedProperty(
        task_id="guard_test_001",
        model="test",
        attempt=1,
        xml="""
<beginning>
    <property
        value="COMPUTE"
        property_id="201"
        type_property="ATTACK"
        description="test">

        <event
            value="COMPUTE"
            event_id="1"
            description="test"
            boolean_expression="(ngap.amf_ue_id > 0)"/>

    </property>
</beginning>
""".strip(),
    )


def test_guard_moves_embedded_logic_leakage_to_detection():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 0.5,
                    "justification": (
                        "Protocol is correct, but the "
                        "embedded function receives the "
                        "wrong state."
                    ),
                    "issues": [
                        {
                            "type":
                                "semantic_mismatch",
                            "message": (
                                "The embedded function "
                                "interprets its argument "
                                "incorrectly."
                            ),
                            "evidence": (
                                "#em_check_ngap_count("
                                "ngap.amf_ue_id)"
                            ),
                        }
                    ],
                },
                "temporal_ordering_semantics": {
                    "score": 0.5,
                    "justification": (
                        "Embedded function does not "
                        "maintain state."
                    ),
                    "issues": [
                        {
                            "type":
                                "property_logic_error",
                            "message": (
                                "The embedded function "
                                "does not maintain state."
                            ),
                            "evidence": (
                                "em_check_ngap_count"
                            ),
                        }
                    ],
                },
                "detection_semantics": {
                    "score": 0.0,
                    "justification": (
                        "Counting is incomplete."
                    ),
                    "issues": [
                        {
                            "type":
                                "property_logic_error",
                            "message": (
                                "No per-identifier "
                                "counter update exists."
                            ),
                            "evidence": (
                                "em_check_ngap_count"
                            ),
                        }
                    ],
                },
                "attribute_relevance": {
                    "score": 0.5,
                    "justification": (
                        "Attribute is relevant, but the "
                        "embedded function mishandles it."
                    ),
                    "issues": [
                        {
                            "type":
                                "semantic_mismatch",
                            "message": (
                                "The embedded function "
                                "mishandles "
                                "ngap.amf_ue_id."
                            ),
                            "evidence": (
                                "#em_check_ngap_count("
                                "ngap.amf_ue_id)"
                            ),
                        }
                    ],
                },
                "summary": "Raw reviewer summary.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_embedded_property()
            ),
            assessment=assessment,
        )
    )

    normalized = result.assessment

    assert (
        normalized
        .message_exchange_semantics
        .score
        == 1.0
    )

    assert (
        normalized
        .message_exchange_semantics
        .issues
        == []
    )

    assert (
        normalized
        .temporal_ordering_semantics
        .score
        == 1.0
    )

    assert (
        normalized
        .temporal_ordering_semantics
        .issues
        == []
    )

    assert (
        normalized
        .attribute_relevance
        .score
        == 1.0
    )

    assert (
        normalized
        .attribute_relevance
        .issues
        == []
    )

    assert (
        normalized
        .detection_semantics
        .score
        == 0.0
    )

    assert (
        len(
            normalized
            .detection_semantics
            .issues
        )
        == 4
    )

    assert len(
        result.actions
    ) == 3


def test_guard_does_not_move_real_temporal_issue():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "temporal_ordering_semantics": {
                    "score": 0.0,
                    "justification": (
                        "Wrong time window."
                    ),
                    "issues": [
                        {
                            "type":
                                "temporal_mismatch",
                            "message": (
                                "The task requires "
                                "5 seconds but the "
                                "property uses 10."
                            ),
                            "evidence": (
                                'delay_max="10"'
                            ),
                        }
                    ],
                },
                "detection_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "attribute_relevance": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "summary": "Temporal mismatch.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_embedded_property()
            ),
            assessment=assessment,
        )
    )

    assert (
        result
        .assessment
        .temporal_ordering_semantics
        .score
        == 0.0
    )

    assert len(
        result
        .assessment
        .temporal_ordering_semantics
        .issues
    ) == 1

    assert result.actions == ()


def test_guard_does_nothing_without_embedded_functions():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "temporal_ordering_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "detection_semantics": {
                    "score": 0.0,
                    "justification": (
                        "Property logic is wrong."
                    ),
                    "issues": [
                        {
                            "type":
                                "property_logic_error",
                            "message": (
                                "Property logic is wrong."
                            ),
                            "evidence":
                                "(ngap.amf_ue_id > 0)",
                        }
                    ],
                },
                "attribute_relevance": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "summary": "Detection issue.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_plain_property()
            ),
            assessment=assessment,
        )
    )

    assert (
        result.assessment
        == assessment
    )

    assert result.actions == ()

def test_guard_moves_security_c_type_mismatch_to_detection():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 0.0,
                    "justification": (
                        "Parameter representation is wrong."
                    ),
                    "issues": [
                        {
                            "type":
                                "property_logic_error",
                            "message": (
                                "The C parameter type is "
                                "incompatible with the supplied "
                                "security_c_type for "
                                "ngap.amf_ue_id."
                            ),
                            "evidence": (
                                "security_c_type is double, "
                                "but the function parameter is "
                                "const void *."
                            ),
                        }
                    ],
                },
                "temporal_ordering_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "detection_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "attribute_relevance": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "summary": "Raw reviewer summary.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_embedded_property()
            ),
            assessment=assessment,
        )
    )

    normalized = result.assessment

    assert (
        normalized
        .message_exchange_semantics
        .score
        == 1.0
    )

    assert (
        normalized
        .message_exchange_semantics
        .issues
        == []
    )

    assert (
        normalized
        .detection_semantics
        .score
        == 0.0
    )

    assert len(
        normalized
        .detection_semantics
        .issues
    ) == 1

    assert (
        normalized
        .detection_semantics
        .issues[0]
        .type
        == "property_logic_error"
    )

    assert len(
        result.actions
    ) == 1

def test_guard_does_not_move_knowledge_missing():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 0.5,
                    "justification": (
                        "Required runtime knowledge "
                        "is unavailable."
                    ),
                    "issues": [
                        {
                            "type":
                                "knowledge_missing",
                            "message": (
                                "The embedded function "
                                "depends on an MMT runtime "
                                "behavior that cannot be "
                                "established."
                            ),
                            "evidence": (
                                "#em_check_ngap_count(...)"
                            ),
                        }
                    ],
                },
                "temporal_ordering_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "detection_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "attribute_relevance": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "summary": "Missing knowledge.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_embedded_property()
            ),
            assessment=assessment,
        )
    )

    assert (
        result
        .assessment
        .message_exchange_semantics
        .score
        == 0.5
    )

    assert len(
        result
        .assessment
        .message_exchange_semantics
        .issues
    ) == 1

    assert (
        result
        .assessment
        .message_exchange_semantics
        .issues[0]
        .type
        == "knowledge_missing"
    )

    assert result.actions == ()

def test_guard_does_not_move_non_embedded_semantic_mismatch():
    assessment = (
        SemanticAssessment.model_validate(
            {
                "message_exchange_semantics": {
                    "score": 0.5,
                    "justification": (
                        "Protocol operation does not "
                        "match the task."
                    ),
                    "issues": [
                        {
                            "type":
                                "semantic_mismatch",
                            "message": (
                                "The selected NGAP "
                                "procedure does not "
                                "represent the requested "
                                "operation."
                            ),
                            "evidence": (
                                "ngap.procedure_code == 4"
                            ),
                        }
                    ],
                },
                "temporal_ordering_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "detection_semantics": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "attribute_relevance": {
                    "score": 1.0,
                    "justification": "Aligned.",
                    "issues": [],
                },
                "summary": "Protocol mismatch.",
                "recommendations": [],
            }
        )
    )

    result = (
        SemanticAssessmentGuard()
        .normalize(
            task=make_task(),
            generated_property=(
                make_embedded_property()
            ),
            assessment=assessment,
        )
    )

    assert (
        result.assessment
        == assessment
    )

    assert result.actions == ()