from typing import Any, List, Optional

import dspy
from pydantic import BaseModel, Field


class CommandArgument(BaseModel):
    name: str = Field(..., description="Argument name")
    type: str = Field(..., description="Python type hint (str, int, bool, Optional[str])")
    required: bool = Field(..., description="Whether the argument is required")
    help: str = Field(..., description="Help text for the argument")


class CommandOption(BaseModel):
    name: str = Field(..., description="Long option name (e.g. --verbose)")
    short: Optional[str] = Field(None, description="Short option name (e.g. -v)")
    type: str = Field(..., description="Python type hint")
    default: Optional[Any] = Field(None, description="Default value")
    help: str = Field(..., description="Help text for the option")


class AgentSpec(BaseModel):
    name: str = Field(..., description="Name of the agent")
    purpose: str = Field(..., description="What this agent does")
    exists: bool = Field(..., description="Whether it already exists")
    file_path: str = Field(..., description="Path to agent file")


class FileSpec(BaseModel):
    path: str = Field(..., description="File path to create")
    content: str = Field(..., description="File content")


class CommandSpec(BaseModel):
    command_name: str = Field(..., description="Kebab-case command name")
    description: str = Field(..., description="Brief CLI help description")
    arguments: List[CommandArgument] = Field(default_factory=list, description="List of arguments")
    options: List[CommandOption] = Field(default_factory=list, description="List of options")
    workflow_steps: List[str] = Field(..., description="Step-by-step description of the workflow")
    agents_needed: List[AgentSpec] = Field(
        default_factory=list, description="Agents to use or create"
    )
    files_to_create: List[FileSpec] = Field(..., description="Files to generate")
    cli_registration: str = Field(..., description="Python code to register the command in cli.py")


class CommandGenerator(dspy.Signature):
    """
    You are a CLI Command Generation Specialist. Your role is to create new CLI commands
    for the Compounding Engineering based on natural language descriptions.

    ## Command Generation Protocol
    1. Analyze Request (inputs, outputs, patterns).
    2. Design Command (name, args, workflow).
    3. Generate Implementation (workflow code, agents, registration).
    """

    command_description: str = dspy.InputField(
        desc="Natural language description of what the command should do"
    )
    existing_commands: str = dspy.InputField(
        desc="List of existing commands and their descriptions for reference"
    )
    existing_agents: str = dspy.InputField(desc="List of existing agents that could be reused")
    project_structure: str = dspy.InputField(desc="Current project structure and conventions")
    command_spec: CommandSpec = dspy.OutputField(desc="Structured command specification")
