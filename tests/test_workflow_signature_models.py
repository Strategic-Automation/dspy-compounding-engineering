from pydantic import BaseModel

from agents.schema.base import MarkdownCompressionRequest, MarkdownCompressionResult
from agents.schema.workflow import (
    GeneratedAgentSpec,
    PlanExecutionResult,
    TodoResolutionResult,
    TriagePresentation,
)
from agents.workflow.agent_generator import AgentGenerator
from agents.workflow.triage_agent import TriageAgent
from agents.workflow.work_plan_executor import PlanExecutionSignature
from agents.workflow.work_todo_executor import TodoResolutionSignature
from utils.knowledge.compression import CompressMarkdown


def _field_annotation(signature_cls, field_name):
    return signature_cls.fields[field_name].annotation


def _output_field_names(signature_cls):
    return set(signature_cls.output_fields)


def test_plan_execution_signature_uses_single_structured_result():
    assert _output_field_names(PlanExecutionSignature) == {"execution_result"}
    assert _field_annotation(PlanExecutionSignature, "execution_result") is PlanExecutionResult
    assert issubclass(PlanExecutionResult, BaseModel)

    result = PlanExecutionResult(
        execution_summary="Updated plan implementation.",
        files_modified=["workflows/work.py"],
        reasoning_trace="Read, edited, verified.",
        verification_status={"workflows/work.py": "passed"},
        success_status=True,
    )

    assert result.execution_summary == "Updated plan implementation."
    assert result.files_modified == ["workflows/work.py"]
    assert result.verification_status["workflows/work.py"] == "passed"
    assert result.success_status is True


def test_todo_resolution_signature_uses_single_structured_result():
    assert _output_field_names(TodoResolutionSignature) == {"resolution_result"}
    assert _field_annotation(TodoResolutionSignature, "resolution_result") is TodoResolutionResult
    assert issubclass(TodoResolutionResult, BaseModel)

    result = TodoResolutionResult(
        resolution_summary="Resolved todo.",
        files_modified=["agents/workflow/work_todo_executor.py"],
        reasoning_trace="Inspected and verified todo resolution.",
        verification_status={"agents/workflow/work_todo_executor.py": "passed"},
        success_status=True,
    )

    assert result.resolution_summary == "Resolved todo."
    assert result.files_modified == ["agents/workflow/work_todo_executor.py"]
    assert result.success_status is True


def test_triage_agent_signature_uses_single_structured_presentation():
    assert _output_field_names(TriageAgent) == {"triage_presentation"}
    assert _field_annotation(TriageAgent, "triage_presentation") is TriagePresentation
    assert issubclass(TriagePresentation, BaseModel)

    presentation = TriagePresentation(
        formatted_presentation="Issue #1: No action required",
        proposed_solution="Close as already passing.",
        action_required=False,
    )

    assert presentation.formatted_presentation.startswith("Issue #1")
    assert presentation.proposed_solution == "Close as already passing."
    assert presentation.action_required is False


def test_agent_generator_signature_uses_single_generated_agent_spec():
    assert _output_field_names(AgentGenerator) == {"generated_agent"}
    assert _field_annotation(AgentGenerator, "generated_agent") is GeneratedAgentSpec
    assert issubclass(GeneratedAgentSpec, BaseModel)

    spec = GeneratedAgentSpec(
        file_name="example_reviewer.py",
        class_name="ExampleReviewer",
        agent_name="Example-Reviewer",
        applicable_languages=["python"],
        code_content="import dspy\n",
    )

    assert spec.file_name == "example_reviewer.py"
    assert spec.class_name == "ExampleReviewer"
    assert spec.agent_name == "Example-Reviewer"
    assert spec.applicable_languages == ["python"]
    assert spec.code_content == "import dspy\n"


def test_compress_markdown_signature_uses_structured_models():
    assert set(CompressMarkdown.input_fields) == {"compression_request"}
    assert _output_field_names(CompressMarkdown) == {"compression_result"}
    assert _field_annotation(CompressMarkdown, "compression_request") is MarkdownCompressionRequest
    assert _field_annotation(CompressMarkdown, "compression_result") is MarkdownCompressionResult
    assert issubclass(MarkdownCompressionRequest, BaseModel)
    assert issubclass(MarkdownCompressionResult, BaseModel)

    request = MarkdownCompressionRequest(content="# Title\n\nDetails", ratio=0.5)
    result = MarkdownCompressionResult(compressed_content="# Title\n\nShort details")

    assert request.content == "# Title\n\nDetails"
    assert request.ratio == 0.5
    assert result.compressed_content == "# Title\n\nShort details"
