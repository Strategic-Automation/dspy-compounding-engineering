from typing import Dict, List, Optional

from pydantic import Field

from agents.schema.base import BaseResearchReport, WorkflowResult


class PlanReport(BaseResearchReport):
    """Structured report for a feature implementation or bug fix plan."""

    overview: str = Field(..., description="High-level description of the plan")
    problem_statement: str = Field(..., description="Why this change matters")
    proposed_solution: str = Field(..., description="High-level implementation approach")
    technical_considerations: List[str] = Field(
        default_factory=list, description="Architecture, performance, security, and etc."
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="List of requirements that must be met"
    )
    implementation_steps: List[str] = Field(
        default_factory=list, description="Step-by-step tasks for implementation"
    )


class PlanExecutionResult(WorkflowResult):
    """Structured result returned after executing a plan."""

    execution_summary: str = Field(
        ..., description="What was accomplished while executing the plan"
    )
    files_modified: List[str] = Field(
        default_factory=list, description="List of files changed during plan execution"
    )
    reasoning_trace: str = Field(..., description="Step-by-step ReAct reasoning process")
    verification_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Verification results for each modified file. Key=filename, Value=status",
    )
    success_status: bool = Field(..., description="Whether plan execution was successful")


class TodoResolutionResult(WorkflowResult):
    """Structured result returned after resolving a todo."""

    resolution_summary: str = Field(
        ..., description="What was accomplished while resolving the todo"
    )
    files_modified: List[str] = Field(
        default_factory=list, description="List of files changed during todo resolution"
    )
    reasoning_trace: str = Field(..., description="Step-by-step ReAct reasoning process")
    verification_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Verification results for each modified file. Key=filename, Value=status",
    )
    success_status: bool = Field(..., description="Whether todo resolution was successful")


class TriagePresentation(WorkflowResult):
    """Structured presentation and decision for a triaged finding."""

    formatted_presentation: str = Field(..., description="The formatted presentation for triage")
    proposed_solution: str = Field(
        ..., description="The specific proposed solution or recommended action to be taken"
    )
    action_required: bool = Field(
        ...,
        description="False if no code changes are needed; True if action or changes are required",
    )


class GeneratedAgentSpec(WorkflowResult):
    """Structured specification for a generated review agent file."""

    file_name: str = Field(..., description="Snake-case file name, e.g. sql_injection_reviewer.py")
    class_name: str = Field(..., description="CamelCase class name, e.g. SqlInjectionReviewer")
    agent_name: str = Field(
        ..., description="Hyphenated agent name for CLI use, e.g. SQL-Injection-Reviewer"
    )
    applicable_languages: Optional[List[str]] = Field(
        None, description="List of languages this agent applies to, or None for all languages"
    )
    code_content: str = Field(
        ...,
        description="Full Python file content including imports and dspy.Signature class",
    )
