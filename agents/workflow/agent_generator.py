from typing import List, Optional

import dspy
from pydantic import BaseModel, Field


class AgentFileSpec(BaseModel):
    file_name: str = Field(..., description="Snake-case file name (e.g. sql_injection_reviewer.py)")
    class_name: str = Field(..., description="CamelCase class name (e.g. SqlInjectionReviewer)")
    agent_name: str = Field(..., description="Human-readable name (e.g. SQL Injection Reviewer)")
    applicable_languages: Optional[List[str]] = Field(
        None, description="List of languages this agent applies to, or None for all"
    )
    content: str = Field(..., description="Full Python file content including imports and signature")


class AgentGenerator(dspy.Signature):
    """
    You are a DSPy Agent Generation Specialist. Your role is to create high-quality, 
    production-ready Review Agents for the Compounding Engineering platform.

    ## Workflow Protocol:
    1. **Research**: Use tools to examine existing agents in `agents/review/` and retrieve 
       latest best practices from the knowledge base. Understand the project's signature style.
    2. **Design**: Create a `dspy.Signature` class that embodies the requested review rule.
    3. **Implement**: 
       - Use `ClassVar` for metadata: `__agent_name__`, `__agent_category__`, `__agent_severity__`, `applicable_languages`.
       - Use standard `ReviewReport` and `ReviewFinding` from `agents.review.schema`.
       - Write a comprehensive docstring describing the scanning logic.
       - Ensure `action_required` is True if findings exist.
       - Ensure the 'content' field is a valid Python file with actual newlines.

    ## Reference Template:
    ```python
    import dspy
    from typing import ClassVar, Optional, Set
    from pydantic import Field
    from agents.review.schema import ReviewReport, ReviewFinding

    class [ClassName](dspy.Signature):
        \"\"\" [Detailed logic] \"\"\"
        __agent_name__: ClassVar[str] = "[Name]"
        __agent_category__: ClassVar[str] = "code-review"
        __agent_severity__: ClassVar[str] = "p2"
        applicable_languages: ClassVar[Optional[Set[str]]] = {[languages]}

        code_diff: str = dspy.InputField(desc="...")
        review_report: ReviewReport = dspy.OutputField(desc="...")
    ```
    """

    agent_description: str = dspy.InputField(
        desc="Description of what the review agent should check for"
    )
    existing_agents: str = dspy.InputField(desc="List of existing review agents for reference")

    file_name: str = dspy.OutputField(desc="Snake-case file name (e.g. sql_injection_reviewer.py)")
    class_name: str = dspy.OutputField(desc="CamelCase class name (e.g. SqlInjectionReviewer)")
    agent_name: str = dspy.OutputField(desc="Human-readable name (e.g. SQL Injection Reviewer)")
    applicable_languages: List[str] = dspy.OutputField(
        desc="List of languages this agent applies to (e.g. ['python', 'javascript'])"
    )
    code_content: str = dspy.OutputField(desc="Full Python file content including imports and signature")
