import dspy

from utils.agent.tools import get_todo_resolver_tools


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
    - list_dir(path): List files and directories.
    - search_codebase(query, path): Search for string/regex in files.
    - read_file(file_path, start_line, end_line): Read specific lines.
    - edit_file(file_path, edits): Edit specific lines. 'edits' is a list of dicts with
      'start_line', 'end_line', 'content'.
    - gather_context(task): Gather relevant file contents based on a task description.
      Use this at the start of a task to get an overview of relevant code.
    - get_system_status(): Check if Qdrant and API keys are available.

    CRITICAL: When using edit_file, the 'content' MUST NOT include the surrounding lines
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
       - Use 'search_codebase' or 'read_file' to find the exact line numbers of the existing
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
    """
    ReAct-based plan executor that uses centralized tools from
    utils/agent/tools.py for consistent codebase exploration and editing.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        self.tools = get_todo_resolver_tools(base_dir)
        self.react_agent = dspy.ReAct(
            signature=PlanExecutionSignature, tools=self.tools, max_iters=20
        )

    def forward(self, plan_content: str, plan_path: str):
        """Execute plan using ReAct reasoning."""
        return self.react_agent(plan_content=plan_content, plan_path=plan_path)
