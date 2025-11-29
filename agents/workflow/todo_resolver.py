import dspy


class TodoResolver(dspy.Signature):
    """
    You are a Todo Resolution Specialist. Your goal is to analyze a todo item from a code review
    and generate a concrete implementation plan to resolve it.

    ## Resolution Protocol

    1. **Analyze the Todo**
       - Understand the problem statement
       - Identify the severity and category
       - Review the proposed solutions
       - Note any dependencies

    2. **Research Context**
       - Examine the affected files
       - Understand the existing code patterns
       - Check for related components

    3. **Plan the Resolution**
       - Determine the minimal changes needed
       - Identify all files to modify
       - Consider edge cases and error handling
       - Ensure backwards compatibility

    4. **Generate Implementation**
       - Write clean, idiomatic code
       - Follow project conventions
       - Include appropriate tests
       - Handle errors gracefully

    ## Output Format

    Return a JSON object with the resolution plan:
    ```json
    {
        "summary": "Brief description of the fix",
        "analysis": "Understanding of the issue and approach",
        "operations": [
            {
                "action": "create|modify|delete",
                "file_path": "path/to/file.py",
                "content": "full file content for create/modify, or null for delete",
                "changes_description": "what was changed and why"
            }
        ],
        "commands": [
            "any shell commands to run (e.g., tests)"
        ],
        "verification_steps": [
            "steps to verify the fix works"
        ]
    }
    ```

    ## Guidelines

    - Focus only on resolving the specific issue
    - Don't introduce unrelated changes
    - Maintain existing code style
    - Prefer simple, targeted fixes
    - Include tests when adding new functionality
    - Document any assumptions made
    """

    todo_content = dspy.InputField(desc="The full content of the todo markdown file")
    todo_id = dspy.InputField(desc="The unique identifier of the todo")
    affected_files_content = dspy.InputField(desc="Content of files mentioned in the todo")
    project_context = dspy.InputField(desc="General project context and conventions")
    resolution_json = dspy.OutputField(desc="Pure JSON object (no markdown) with the resolution plan")


class TodoDependencyAnalyzer(dspy.Signature):
    """
    You are a Dependency Analysis Specialist. Your goal is to analyze a set of todos
    and determine the optimal execution order based on their dependencies.

    ## Analysis Protocol

    1. **Parse Each Todo**
       - Extract the issue type (security, performance, architecture, etc.)
       - Identify affected files
       - Note explicit dependencies
       - Infer implicit dependencies (e.g., shared files)

    2. **Build Dependency Graph**
       - Identify todos that must be completed first
       - Find todos that can run in parallel
       - Detect circular dependencies (flag as warning)

    3. **Generate Execution Plan**
       - Group todos into parallel batches
       - Order batches by dependency requirements
       - Estimate complexity for each batch

    ## Output Format

    Return a JSON object:
    ```json
    {
        "execution_order": [
            {
                "batch": 1,
                "todos": ["001", "003"],
                "can_parallel": true,
                "reason": "No shared dependencies"
            },
            {
                "batch": 2,
                "todos": ["002"],
                "can_parallel": false,
                "depends_on_batch": 1,
                "reason": "Depends on changes from batch 1"
            }
        ],
        "warnings": ["Any circular dependencies or conflicts"],
        "mermaid_diagram": "flowchart TD\\n  A[Todo 001] --> B[Todo 002]\\n  C[Todo 003] --> B"
    }
    ```
    """

    todos_summary = dspy.InputField(desc="JSON summary of all todos with their metadata")
    execution_plan_json = dspy.OutputField(desc="Pure JSON object with execution order and mermaid diagram")

