import dspy
from utils.file_tools import (
    list_directory,
    search_files,
    read_file_range,
    edit_file_lines,
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
    - edit_file_lines(file_path, edits): Edit specific lines. 'edits' is a list of dicts with 'start_line', 'end_line', 'content'.
    """

    todo_content: str = dspy.InputField(desc="Content of the todo file")
    todo_id: str = dspy.InputField(desc="Unique identifier of the todo")

    resolution_summary: str = dspy.OutputField(desc="What was accomplished")
    files_modified: str = dspy.OutputField(desc="List of files that were changed")
    reasoning_trace: str = dspy.OutputField(desc="Step-by-step ReAct reasoning process")
    verification_status: str = dspy.OutputField(
        desc="Verification results for each modified file. For structured files (TOML/YAML/JSON/Python), confirm syntax is valid. Format: 'filename: verified (syntax valid)' or 'filename: FAILED (syntax error: details)'"
    )
    success_status: str = dspy.OutputField(desc="Whether resolution was successful")


class ReActTodoResolver(dspy.Module):
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
            signature=TodoResolutionSignature, tools=self.tools, max_iters=15
        )

    def forward(self, todo_content: str, todo_id: str):
        """Resolve todo using ReAct reasoning."""
        return self.react_agent(todo_content=todo_content, todo_id=todo_id)
