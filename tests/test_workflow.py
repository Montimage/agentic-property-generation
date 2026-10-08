from property_agent.models import (
    CompilationResult,
    CompilationStatus,
    GeneratedProperty,
    MonitoringTask,
    RepairOutcomeStatus,
    RepairResult,
    RetrievalResult,
    SemanticDimensionResult,
    SemanticReport,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    SemanticIssue,
    SemanticIssueType,
)

from property_agent.workflow import (
    PropertyWorkflow,
    PropertyWorkflowConfig,
    WorkflowDependencies,
)


def valid_validation(
    validator: str,
):
    return ValidationResult(
        validator=validator,
        valid=True,
        issues=[],
    )


def aligned_dimension():
    return SemanticDimensionResult(
        score=1.0,
        justification="Aligned.",
        issues=[],
    )


def valid_semantic_report():
    return SemanticReport(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            aligned_dimension()
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=1.0,
        valid=True,
        summary="Aligned.",
        recommendations=[],
    )

def invalid_repairable_semantic_report():
    """
    Semantic failure that can safely enter the repair
    loop.
    """

    return SemanticReport(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            SemanticDimensionResult(
                score=0.0,
                justification=(
                    "The required detection "
                    "condition is missing."
                ),
                issues=[
                    SemanticIssue(
                        type=(
                            SemanticIssueType
                            .PROPERTY_LOGIC_ERROR
                        ),
                        message=(
                            "The property does not "
                            "implement the required "
                            "detection condition."
                        ),
                        evidence=(
                            "The monitoring task "
                            "requires an additional "
                            "condition."
                        ),
                    )
                ],
            )
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=0.75,
        valid=False,
        summary=(
            "The property requires semantic repair."
        ),
        recommendations=[
            (
                "Represent the missing detection "
                "condition."
            )
        ],
    )


def blocked_semantic_report():
    """
    Semantic uncertainty that must not be repaired
    automatically.
    """

    return SemanticReport(
        message_exchange_semantics=(
            aligned_dimension()
        ),
        temporal_ordering_semantics=(
            aligned_dimension()
        ),
        detection_semantics=(
            SemanticDimensionResult(
                score=0.5,
                justification=(
                    "The task does not define the "
                    "criterion required to complete "
                    "the monitoring rule."
                ),
                issues=[
                    SemanticIssue(
                        type=(
                            SemanticIssueType
                            .TASK_UNDERSPECIFIED
                        ),
                        message=(
                            "The task does not define "
                            "the required threshold."
                        ),
                        evidence=(
                            "The task refers to an "
                            "abnormal amount without "
                            "defining the criterion."
                        ),
                    )
                ],
            )
        ),
        attribute_relevance=(
            aligned_dimension()
        ),
        overall_score=0.875,
        valid=False,
        summary=(
            "The task is underspecified."
        ),
        recommendations=[],
    )

class FakeRepairableSemanticReviewer:
    """
    First review fails semantically.

    After one repair, the second review succeeds.
    """

    def __init__(self):
        self.call_count = 0

    def review(
        self,
        task,
        generated_property,
    ):
        self.call_count += 1

        if self.call_count == 1:
            return (
                invalid_repairable_semantic_report()
            )

        return valid_semantic_report()

class FakeBlockedSemanticReviewer:
    def __init__(self):
        self.call_count = 0

    def review(
        self,
        task,
        generated_property,
    ):
        self.call_count += 1

        return blocked_semantic_report()

def test_workflow_repairs_semantic_failure():
    retriever = FakeRetriever()

    generator = FakeGenerator()

    semantic_reviewer = (
        FakeRepairableSemanticReviewer()
    )

    repairer = FakeRepairer()

    compiler = FakeCompilationClient()

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=lambda xml: (
            valid_validation(
                "mmt_syntax"
            )
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    state = workflow.invoke(
        make_task()
    )

    result = state["result"]

    assert result.success is True

    assert state["repair_count"] == 1

    # Semantic review occurs once before repair
    # and once after repaired deterministic
    # validation succeeds.
    assert (
        semantic_reviewer.call_count
        == 2
    )

    assert repairer.call_count == 1

    assert compiler.call_count == 1

    assert (
        len(
            state["property_history"]
        )
        == 2
    )

    assert (
        result.final_assessment.status.value
        == "accepted"
    )

def test_workflow_blocks_underspecified_task():
    retriever = FakeRetriever()

    generator = FakeGenerator()

    semantic_reviewer = (
        FakeBlockedSemanticReviewer()
    )

    repairer = FakeRepairer()

    compiler = FakeCompilationClient()

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=lambda xml: (
            valid_validation(
                "mmt_syntax"
            )
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    state = workflow.invoke(
        make_task()
    )

    result = state["result"]

    assert result.success is False

    assert (
        state["terminal_reason"]
        == "repair_blocked"
    )

    assert repairer.call_count == 0

    assert compiler.call_count == 0

    assert (
        semantic_reviewer.call_count
        == 1
    )

    assert (
        result.final_assessment
        is not None
    )

    assert (
        result.final_assessment.status.value
        == "blocked"
    )

    assert (
        result.repair_result
        is not None
    )

    assert (
        result.repair_result.status
        == RepairOutcomeStatus.BLOCKED
    )

class FakeIneffectiveRepairer:
    """
    Produces a new attempt but deliberately preserves
    the synthetic validation problem.
    """

    def __init__(self):
        self.call_count = 0

    def repair(
        self,
        task,
        current_property,
        diagnosis,
        semantic_report=None,
    ):
        self.call_count += 1

        repaired = GeneratedProperty(
            task_id=task.id,
            xml=current_property.xml,
            model="fake/repair",
            attempt=(
                current_property.attempt
                + 1
            ),
        )

        return RepairResult(
            task_id=task.id,
            status=(
                RepairOutcomeStatus.REPAIRED
            ),
            diagnosis=diagnosis,
            repaired_property=repaired,
        )

def test_workflow_stops_at_repair_limit():
    retriever = FakeRetriever()

    generator = FakeGenerator(
        xml_marker="BAD_SYNTAX"
    )

    semantic_reviewer = (
        FakeSemanticReviewer()
    )

    repairer = (
        FakeIneffectiveRepairer()
    )

    compiler = FakeCompilationClient()

    def always_failing_syntax(
        xml: str,
    ):
        return ValidationResult(
            validator="mmt_syntax",
            valid=False,
            issues=[
                ValidationIssue(
                    code=(
                        "TEST_SYNTAX_ERROR"
                    ),
                    message=(
                        "Synthetic persistent "
                        "syntax failure."
                    ),
                    severity=(
                        ValidationSeverity.ERROR
                    ),
                )
            ],
        )

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=(
            always_failing_syntax
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    state = workflow.invoke(
        make_task()
    )

    result = state["result"]

    assert result.success is False

    assert (
        state["terminal_reason"]
        == "repair_limit_reached"
    )

    assert state["repair_count"] == 2

    assert repairer.call_count == 2

    # Initial candidate + two repaired candidates.
    assert (
        len(
            state["property_history"]
        )
        == 3
    )

    assert (
        state["property_history"][0].attempt
        == 1
    )

    assert (
        state["property_history"][1].attempt
        == 2
    )

    assert (
        state["property_history"][2].attempt
        == 3
    )

    # Syntax never passed, therefore semantic review
    # and real compilation must never be reached.
    assert (
        semantic_reviewer.call_count
        == 0
    )

    assert compiler.call_count == 0

    assert (
        result.final_assessment.status.value
        == "rejected_validation"
    )

class FakeRejectingCompilationClient:
    def __init__(self):
        self.call_count = 0

    def compile_property(
        self,
        generated_property,
    ):
        self.call_count += 1

        return CompilationResult(
            status=(
                CompilationStatus
                .COMPILATION_FAILED
            ),
            compile_ok=False,
            returncode=1,
            message=(
                "MMT rejected the property."
            ),
            stderr=(
                "Synthetic compiler failure."
            ),
            local_xml_sha256="abc",
            remote_xml_sha256="abc",
            hash_matches=True,
            http_status=422,
        )

def test_compilation_failure_is_terminal():
    retriever = FakeRetriever()

    generator = FakeGenerator()

    semantic_reviewer = (
        FakeSemanticReviewer()
    )

    repairer = FakeRepairer()

    compiler = (
        FakeRejectingCompilationClient()
    )

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=lambda xml: (
            valid_validation(
                "mmt_syntax"
            )
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    state = workflow.invoke(
        make_task()
    )

    result = state["result"]

    assert result.success is False

    assert (
        state["terminal_reason"]
        == "compilation_failed"
    )

    assert compiler.call_count == 1

    # Compiler feedback is final assessment evidence,
    # not another repair signal.
    assert repairer.call_count == 0

    assert (
        result.final_assessment.status.value
        == "rejected_compilation"
    )


class FakeRetriever:
    def __init__(self):
        self.call_count = 0

    def retrieve(
        self,
        task,
    ):
        self.call_count += 1

        return RetrievalResult(
            task_id=task.id,
            enabled=False,
            requested_k=2,
            candidate_count=0,
            examples=[],
        )


class FakeGenerator:
    def __init__(
        self,
        xml_marker="VALID",
    ):
        self.xml_marker = xml_marker
        self.call_count = 0

    def generate(
        self,
        task,
        retrieval_result=None,
    ):
        self.call_count += 1

        return GeneratedProperty(
            task_id=task.id,
            xml=(
                "<beginning>"
                f"<!-- {self.xml_marker} -->"
                "<property "
                'value="COMPUTE" '
                f'property_id="{task.property_id}" '
                'description="Test" '
                'type_property="SECURITY">'
                "<event "
                'value="COMPUTE" '
                'event_id="1" '
                'description="Test" '
                'boolean_expression="'
                'ngap.procedure_code == 4"/>'
                "</property>"
                "</beginning>"
            ),
            model="fake/generator",
            attempt=1,
        )


class FakeSemanticReviewer:
    def __init__(self):
        self.call_count = 0

    def review(
        self,
        task,
        generated_property,
    ):
        self.call_count += 1

        return valid_semantic_report()


class FakeRepairer:
    def __init__(self):
        self.call_count = 0

    def repair(
        self,
        task,
        current_property,
        diagnosis,
        semantic_report=None,
    ):
        self.call_count += 1

        repaired = GeneratedProperty(
            task_id=task.id,
            xml=(
                current_property.xml
                .replace(
                    "BAD_SYNTAX",
                    "VALID",
                )
            ),
            model="fake/repair",
            attempt=(
                current_property.attempt
                + 1
            ),
        )

        return RepairResult(
            task_id=task.id,
            status=(
                RepairOutcomeStatus.REPAIRED
            ),
            diagnosis=diagnosis,
            repaired_property=repaired,
        )


class FakeCompilationClient:
    def __init__(self):
        self.call_count = 0

    def compile_property(
        self,
        generated_property,
    ):
        self.call_count += 1

        return CompilationResult(
            status=(
                CompilationStatus.COMPILED
            ),
            compile_ok=True,
            returncode=0,
            local_xml_sha256="abc",
            remote_xml_sha256="abc",
            hash_matches=True,
        )


def make_task():
    return MonitoringTask(
        id="workflow_test",
        property_id="701",
        description="Monitor an NGAP event.",
        protocols=["ngap"],
    )

def test_workflow_happy_path():
    retriever = FakeRetriever()
    generator = FakeGenerator()

    semantic_reviewer = (
        FakeSemanticReviewer()
    )

    repairer = FakeRepairer()

    compiler = (
        FakeCompilationClient()
    )

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=lambda xml: (
            valid_validation(
                "mmt_syntax"
            )
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    result = workflow.run(
        make_task()
    )

    assert result.success is True

    assert (
        result.final_assessment
        is not None
    )

    assert (
        result.final_assessment.status.value
        == "accepted"
    )

    assert retriever.call_count == 1

    assert generator.call_count == 1

    assert (
        semantic_reviewer.call_count
        == 1
    )

    assert repairer.call_count == 0

    assert compiler.call_count == 1

def test_workflow_repairs_then_revalidates():
    retriever = FakeRetriever()

    generator = FakeGenerator(
        xml_marker="BAD_SYNTAX"
    )

    semantic_reviewer = (
        FakeSemanticReviewer()
    )

    repairer = FakeRepairer()

    compiler = (
        FakeCompilationClient()
    )

    def syntax_validator(
        xml: str,
    ):
        if "BAD_SYNTAX" in xml:
            return ValidationResult(
                validator="mmt_syntax",
                valid=False,
                issues=[
                    ValidationIssue(
                        code=(
                            "TEST_SYNTAX_ERROR"
                        ),
                        message=(
                            "Synthetic syntax "
                            "failure."
                        ),
                        severity=(
                            ValidationSeverity.ERROR
                        ),
                    )
                ],
            )

        return valid_validation(
            "mmt_syntax"
        )

    dependencies = WorkflowDependencies(
        generator=generator,
        semantic_reviewer=(
            semantic_reviewer
        ),
        repairer=repairer,
        retriever=retriever,
        compilation_client=compiler,
        xml_validator=lambda xml: (
            valid_validation("xml")
        ),
        syntax_validator=(
            syntax_validator
        ),
        static_validator=lambda xml: (
            valid_validation(
                "mmt_static"
            )
        ),
    )

    workflow = PropertyWorkflow(
        dependencies=dependencies,
        config=PropertyWorkflowConfig(
            max_repair_attempts=2,
            save_artifacts=False,
        ),
    )

    state = workflow.invoke(
        make_task()
    )

    result = state["result"]

    assert result.success is True

    assert (
        state["repair_count"]
        == 1
    )

    assert (
        len(
            state[
                "property_history"
            ]
        )
        == 2
    )

    assert (
        state[
            "property_history"
        ][0].attempt
        == 1
    )

    assert (
        state[
            "property_history"
        ][1].attempt
        == 2
    )

    # Retrieval occurred only once despite
    # the repair loop.
    assert retriever.call_count == 1

    # Initial generation also occurred once.
    assert generator.call_count == 1

    assert repairer.call_count == 1

    # Semantic review happens only after
    # repaired deterministic validation passes.
    assert (
        semantic_reviewer.call_count
        == 1
    )

    assert compiler.call_count == 1