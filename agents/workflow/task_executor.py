from typing import List, Optional

import dspy
from pydantic import BaseModel, Field


from utils.mcp.client import MCPManager

import subprocess


class FileOperation(BaseModel):
    action: str = Field(..., description="create|modify|delete")
    file_path: str = Field(..., description="Path to the file")
    content: Optional[str] = Field(
        None, description="Full file content for create, or null for delete"
    )
    changes_description: str = Field(..., description="Description of what was changed and why")


class TaskExecution(BaseModel):
    summary: str = Field(..., description="Brief description of changes made")
    operations: List[FileOperation] = Field(..., description="List of file operations to perform")
    commands: List[str] = Field(
        default_factory=list,
        description="Shell commands to run (e.g., migrations, installs)",
    )
    next_steps: List[str] = Field(default_factory=list, description="Follow-up actions needed")


# Global MCP Manager (initialize when needed)
_mcp_manager = None

def get_mcp_tools() -> List[dspy.Tool]:
    """Retrieves all standard tools from the MCP ecosystem."""
    global _mcp_manager
    if not _mcp_manager:
        _mcp_manager = MCPManager()
        _mcp_manager.connect_all()
    # The client creates wrapped dspy.Tool instances
    return _mcp_manager.get_all_tools()



class TaskExecutor(dspy.Signature):
    """
    You are a Task Execution Specialist. Your goal is to generate the implementation
    for a specific task within a larger plan.

    ## Execution Protocol
    1. Understand requirements and dependencies.
    2. Plan implementation (files, order, edge cases).
    3. Generate clean, idiomatic code following project conventions.
    """

    task_title: str = dspy.InputField(desc="The title of the task to execute")
    task_description: str = dspy.InputField(desc="Detailed description of what needs to be done")
    task_files: str = dspy.InputField(desc="List of files likely to be affected")
    task_acceptance_criteria: str = dspy.InputField(desc="Criteria for task completion")
    existing_code_context: str = dspy.InputField(desc="Relevant existing code from the project")
    project_conventions: str = dspy.InputField(desc="Project coding conventions and patterns")

    execution_result: TaskExecution = dspy.OutputField(
        desc="Structured execution plan with operations and commands"
    )
