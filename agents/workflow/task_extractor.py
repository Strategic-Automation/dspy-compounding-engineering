from typing import List
from pydantic import BaseModel, Field
import dspy


class ExtractedTask(BaseModel):
    id: int = Field(..., description="Sequential task ID")
    title: str = Field(..., description="Actionable task title")
    description: str = Field(
        ..., description="Detailed description of what needs to be done"
    )
    files: List[str] = Field(
        default_factory=list, description="Files likely to be affected"
    )
    depends_on: List[int] = Field(
        default_factory=list, description="IDs of tasks this depends on"
    )
    complexity: str = Field(..., description="small, medium, or large")
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="List of criteria for completion"
    )


class TaskList(BaseModel):
    tasks: List[ExtractedTask] = Field(
        ..., description="Ordered list of extracted tasks"
    )


class TaskExtractor(dspy.Signature):
    """
    You are a Task Extraction Specialist. Your goal is to analyze a plan document and extract
    a structured list of actionable implementation tasks.

    ## Analysis Protocol
    1. Parse Plan Structure (goal, tasks, criteria, dependencies).
    2. Extract Tasks (title, description, files, complexity).
    3. Order Tasks (foundation -> core -> integration -> tests).
    """

    plan_content: str = dspy.InputField(
        desc="The markdown plan content to extract tasks from"
    )
    project_context: str = dspy.InputField(
        desc="Brief context about the project structure and conventions"
    )
    extraction_result: TaskList = dspy.OutputField(
        desc="Structured list of extracted tasks"
    )
