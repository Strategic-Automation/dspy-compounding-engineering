import dspy
from utils.file_tools import (
    list_directory,
    search_files,
    read_file_range,
    edit_file_lines,
)


class PlanExecutionSignature(dspy.Signature):
    """You are a Plan Execution Specialist using ReAct reasoning.

    Execute the steps outlined in the plan file. Use tools to examine the codebase,
    make necessary changes, and verify your work.

    You have access to the following tools:
    - list_directory(path): List files and directories.
    - search_files(query, path, regex): Search for string/regex in files.
    - read_file_range(file_path, start_line, end_line): Read specific lines.
    - edit_file_lines(file_path, edits): Edit specific lines. 'edits' is a list of dicts with 'start_line', 'end_line', 'content'.
    """

    plan_content = dspy.InputField(desc="Content of the plan file")
    plan_path = dspy.InputField(desc="Path to the plan file")

    execution_summary = dspy.OutputField(desc="What was accomplished")
    files_modified = dspy.OutputField(desc="List of files that were changed")
    reasoning_trace = dspy.OutputField(desc="Step-by-step ReAct reasoning process")
    success_status = dspy.OutputField(desc="Whether execution was successful")


class ReActPlanExecutor(dspy.Module):
    def __init__(self, base_dir: str = "."):
        super().__init__()

        # Define tools with base_dir bound
        from functools import partial

        self.tools = [
            partial(list_directory, base_dir=base_dir),
            partial(search_files, base_dir=base_dir),
            partial(read_file_range, base_dir=base_dir),
            partial(edit_file_lines, base_dir=base_dir),
        ]

        # Update tool names and docstrings to match originals (needed for dspy)
        for tool in self.tools:
            if hasattr(tool, "func"):
                tool.__name__ = tool.func.__name__
                tool.__doc__ = tool.func.__doc__

        # Create ReAct agent
        self.react_agent = dspy.ReAct(
            signature=PlanExecutionSignature, tools=self.tools, max_iters=20
        )

    def forward(self, plan_content: str, plan_path: str):
        """Execute plan using ReAct reasoning."""
        return self.react_agent(plan_content=plan_content, plan_path=plan_path)
