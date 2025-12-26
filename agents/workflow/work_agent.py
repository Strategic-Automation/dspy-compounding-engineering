import dspy

from utils.io import (
    edit_file_lines,
    get_project_context,
    get_system_status,
    list_directory,
    read_file_range,
    search_files,
)


class PlanExecutionSignature(dspy.Signature):
    """You are a Plan Execution Specialist using ReAct reasoning.

    Execute the steps outlined in the plan file. Use tools to examine the codebase,
    make necessary changes, and verify your work.

    CRITICAL VERIFICATION REQUIREMENTS:

    1. AFTER completing all edits, you MUST read back the changed sections
       of ALL modified files to ensure the changes were applied correctly.

    2. FOR STRUCTURED FILES, you MUST validate syntax:
       - TOML files (.toml): Verify brackets, quotes, and structure are valid
       - YAML files (.yaml, .yml): Verify indentation and structure
       - JSON files (.json): Verify brackets, braces, quotes, commas
       - Python files (.py): Verify no syntax errors (missing colons, brackets, etc.)

    3. If you detect any syntax errors during verification:
       - Re-edit the file to fix the error
       - Re-verify until the file is valid
       - Do NOT mark the task complete with syntax errors

    Do not assume success without these verification steps. Syntax errors in
    configuration files (like pyproject.toml) can break the entire system.

    You have access to the following tools:
    - list_directory(path): List files and directories.
    - search_files(query, path, regex): Search for string/regex in files.
    - read_file_range(file_path, start_line, end_line): Read specific lines.
    - edit_file_lines(file_path, edits): Edit specific lines. 'edits' is a list of dicts with
      'start_line', 'end_line', 'content'.
    - get_project_context(task): Gather relevant file contents based on a task description.
      Use this at the start of a task to get an overview of relevant code.
    - get_system_status(): Check if Qdrant and API keys are available.

    CRITICAL: When using edit_file_lines, the 'content' MUST NOT include the surrounding lines
    (context) unless you INTEND to duplicate them.
    - If you want to replace line 10, 'edits' should be [{'start_line': 10, 'end_line': 10,
      'content': 'new_line_10_content'}].
    - DO NOT include lines 9 or 11 in 'content' unless you are changing them too.
    - TRIPLE QUOTES (''') HAZARD: When editing docstrings or multiline strings, be careful not
      to break the tool call syntax.

    4. PREVENT DUPLICATION:
       - Before adding a new function, class, or variable, ALWAYS check if it already exists in
         the file.
       - If it does, you MUST replace the existing definition (using the correct line range)
         instead of appending a new one.
       - Use 'search_files' or 'read_file_range' to find the exact line numbers of the existing
         code before editing.
    """

    plan_content: str = dspy.InputField(desc="Content of the plan file")
    plan_path: str = dspy.InputField(desc="Path to the plan file")

    execution_summary: str = dspy.OutputField(desc="What was accomplished")
    files_modified: list[str] = dspy.OutputField(desc="List of files that were changed")
    reasoning_trace: str = dspy.OutputField(desc="Step-by-step ReAct reasoning process")
    verification_status: dict[str, str] = dspy.OutputField(
        desc="Verification results for each modified file. Key=filename, Value=status"
    )
    success_status: bool = dspy.OutputField(desc="Whether execution was successful")


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
            partial(get_project_context, base_dir=base_dir),
            get_system_status,
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
