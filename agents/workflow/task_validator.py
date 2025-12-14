from typing import List, Optional
import dspy
from pydantic import BaseModel, Field


class CriterionStatus(BaseModel):
    criterion: str = Field(..., description="The acceptance criterion")
    met: bool = Field(..., description="Whether it is met")
    notes: str = Field(..., description="Observations or gaps")


class ValidationIssue(BaseModel):
    severity: str = Field(..., description="error, warning, or info")
    file: str = Field(..., description="File path")
    line: Optional[int] = Field(None, description="Line number")
    message: str = Field(..., description="Description of issue")
    suggestion: str = Field(..., description="How to fix it")


class TestNeeded(BaseModel):
    description: str = Field(..., description="Test case description")
    file: str = Field(..., description="Suggested test file")


class TaskValidation(BaseModel):
    is_valid: bool = Field(..., description="Overall valid status")
    criteria_status: List[CriterionStatus] = Field(
        ..., description="Status of each criterion"
    )
    issues: List[ValidationIssue] = Field(
        default_factory=list, description="Found issues"
    )
    tests_needed: List[TestNeeded] = Field(
        default_factory=list, description="Missing tests"
    )
    ready_to_commit: bool = Field(..., description="Ready for safe commit")
    summary: str = Field(..., description="Overall validation summary")


class TaskValidator(dspy.Signature):
    """
    You are a Task Validation Specialist. Your goal is to validate that a task
    implementation meets its acceptance criteria and follows best practices.

    ## Validation Protocol
    1. Check Acceptance Criteria (met/unmet, gaps).
    2. Code Quality Review (syntax, errors, security).
    3. Integration Check (imports, dependencies).
    4. Test Coverage (missing tests).
    """

    task_title: str = dspy.InputField(desc="The title of the task being validated")
    task_acceptance_criteria: str = dspy.InputField(
        desc="The acceptance criteria to validate against"
    )
    implementation_changes: str = dspy.InputField(
        desc="The code changes that were made"
    )
    test_output: str = dspy.InputField(desc="Output from running tests, if available")
    validation_result: TaskValidation = dspy.OutputField(
        desc="Structured validation results"
    )
