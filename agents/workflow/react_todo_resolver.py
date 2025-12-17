import dspy

from utils.io import (
    create_file,
    edit_file_lines,
    list_directory,
    read_file_range,
    search_files,
)


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
    - list_directory(path): List files and directories.
    - search_files(query, path, regex): Search for string/regex in files.
    - read_file_range(file_path, start_line, end_line): Read specific lines.
    - edit_file_lines(file_path, edits): Edit specific lines. 'edits' is a list of dicts with
      'start_line', 'end_line', 'content'.
    - create_file(file_path, content): Create a new file with content.

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
    def __init__(self, base_dir: str = "."):
        super().__init__()

        # Define tools with base_dir bound and metadata preserved
        def bind_tool(func):
            def wrapper(*args, **kwargs):
                return func(*args, base_dir=base_dir, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        self.tools = [
            bind_tool(list_directory),
            bind_tool(search_files),
            bind_tool(read_file_range),
            bind_tool(edit_file_lines),
            bind_tool(create_file),
        ]

        # Create ReAct agent
        self.react_agent = dspy.ReAct(
            signature=TodoResolutionSignature, tools=self.tools, max_iters=15
        )

    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text to remove potentially dangerous characters."""
        if not text:
            return ""
        # Basic sanitization: remove null bytes and control characters (except newlines/tabs)
        # and ensure utf-8 encoding compatibility
        return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

    def forward(self, todo_content: str, todo_id: str):
        """Resolve todo using ReAct reasoning."""
        clean_content = self._sanitize_input(todo_content)
        return self.react_agent(todo_content=clean_content, todo_id=todo_id)
