import dspy

from config import settings
from utils.agent.tools import get_todo_resolver_tools


class TodoResolutionSignature(dspy.Signature):
    """You are a file editing specialist using ReAct reasoning.

    Analyze the todo and make necessary file changes through iterative
    reasoning: think about what needs to change, use tools to examine
    and modify files, observe results, and iterate until the todo is resolved.

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
    - create_new_file(file_path, content): Create a new file with content.
    - gather_context(task): Gather relevant file contents based on a task description.
      Use this if you need to find where a specific logic is implemented.
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

    5. DIFF-FIRST WORKFLOW:
       - BEFORE editing, read the exact lines you plan to change
       - COMPARE the old content with your intended new content mentally
       - Only edit if the change is necessary and correct
       - AFTER editing, read the same lines again to confirm

    6. NEWLINE FORMATTING:
       - When writing multi-line content, use ACTUAL line breaks in your content string
       - Do NOT use literal escape sequences like the two characters backslash-n
       - Each line of code should be on its own line in your content
       - Example of CORRECT multi-line content:
         'def foo():
             return bar'
       - Example of WRONG content: 'def foo():\\n    return bar'
    """

    todo_content: str = dspy.InputField(desc="Content of the todo file")
    todo_id: str = dspy.InputField(desc="Unique identifier of the todo")

    resolution_summary: str = dspy.OutputField(desc="What was accomplished")
    files_modified: list[str] = dspy.OutputField(desc="List of files that were changed")
    reasoning_trace: str = dspy.OutputField(desc="Step-by-step ReAct reasoning process")
    verification_status: dict[str, str] = dspy.OutputField(
        desc="Verification results for each modified file. Key=filename, Value=status"
    )
    success_status: bool = dspy.OutputField(desc="Whether resolution was successful")


class ReActTodoResolver(dspy.Module):
    """
    ReAct-based todo resolver that uses centralized tools from
    utils/agent/tools.py for consistent codebase exploration and editing.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        from utils.knowledge import KBPredict

        self.tools = get_todo_resolver_tools(base_dir)
        react = dspy.ReAct(
            signature=TodoResolutionSignature,
            tools=self.tools,
            max_iters=settings.executor_max_iters,
        )
        self.predictor = KBPredict.wrap(
            react,
            kb_tags=["work", "work-resolutions", "code-review", "triage-decisions"],
        )

    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text to remove potentially dangerous characters."""
        if not text:
            return ""
        # Basic sanitization: remove null bytes and control characters
        return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

    def forward(self, todo_content: str, todo_id: str):
        """Resolve todo using ReAct reasoning."""
        clean_content = self._sanitize_input(todo_content)
        return self.predictor(todo_content=clean_content, todo_id=todo_id)
