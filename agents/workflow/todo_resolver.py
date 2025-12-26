from typing import List, Optional

import dspy
from pydantic import BaseModel, Field


class FileOperation(BaseModel):
    action: str = Field(..., description="create|modify|delete")
    file_path: str = Field(..., description="Path to the file")
    content: Optional[str] = Field(
        None, description="Full file content for create/modify, or null for delete"
    )
    changes_description: str = Field(..., description="Description of what was changed and why")


class TodoResolution(BaseModel):
    summary: str = Field(..., description="Brief description of the fix")
    analysis: str = Field(..., description="Understanding of the issue and approach")
    operations: List[FileOperation] = Field(..., description="List of file operations to perform")
    commands: List[str] = Field(
        default_factory=list, description="Shell commands to run (e.g., tests)"
    )
    verification_steps: List[str] = Field(
        default_factory=list, description="Steps to verify the fix works"
    )


class TodoResolver(dspy.Signature):
    """
    You are a Todo Resolution Specialist. Your goal is to analyze a todo item from a code review
    and generate a concrete implementation plan to resolve it.

    ## Resolution Protocol
    1. Analyze the Todo (problem, severity, solutions).
    2. Research Context (affected files, patterns).
    3. Plan the Resolution (minimal changes, edge cases).
    4. Generate Implementation (clean code, tests).
    """

    todo_content: str = dspy.InputField(desc="The full content of the todo markdown file")
    todo_id: str = dspy.InputField(desc="The unique identifier of the todo")
    affected_files_content: str = dspy.InputField(desc="Content of files mentioned in the todo")
    project_context: str = dspy.InputField(desc="General project context and conventions")
    resolution_plan: TodoResolution = dspy.OutputField(desc="Structured resolution plan")


class ExecutionBatch(BaseModel):
    batch: int = Field(..., description="Batch number (1-based)")
    todos: List[str] = Field(..., description="List of todo IDs in this batch")
    can_parallel: bool = Field(..., description="Whether these todos can be run in parallel")
    reason: str = Field(..., description="Reason for grouping/ordering")
    depends_on_batch: Optional[int] = Field(None, description="Batch number this depends on")


class ExecutionPlan(BaseModel):
    execution_order: List[ExecutionBatch] = Field(
        ..., description="Batches of todos in execution order"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Any circular dependencies or conflicts"
    )
    mermaid_diagram: str = Field(..., description="Mermaid flowchart definition")


class TodoDependencyAnalyzer(dspy.Signature):
    """
    You are a Dependency Analysis Specialist. Your goal is to analyze a set of todos
    and determine the optimal execution order based on their dependencies.

    ## Analysis Protocol
    1. Parse Each Todo (type, files, dependencies).
    2. Build Dependency Graph (order, parallelization, cycles).
    3. Generate Execution Plan (batches, complexity).
    """

    todos_summary: str = dspy.InputField(desc="JSON summary of all todos with their metadata")
    execution_plan: ExecutionPlan = dspy.OutputField(
        desc="Structured execution plan with batches and diagram"
    )
