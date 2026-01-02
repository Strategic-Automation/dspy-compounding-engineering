from typing import List, Optional

import dspy
from pydantic import BaseModel, Field


class AgentFileSpec(BaseModel):
    file_name: str = Field(..., description="Target file name (e.g. 'security_scanner.py')")
    class_name: str = Field(..., description="Target class name (e.g. 'SecurityScanner')")
    agent_name: str = Field(..., description="Human-readable agent name")
    applicable_languages: Optional[List[str]] = Field(
        None, description="List of languages this agent applies to, or None for all"
    )
    code_content: str = Field(
        ..., description="Full Python file content including imports and signature"
    )


class AgentGenerator(dspy.Signature):
    """
    You are a DSPy Agent Generation Specialist. Your role is to create high-quality,
    production-ready Review Agents for the Compounding Engineering platform.

    ## Workflow Protocol:
    1. **Research**: Use tools to examine existing agents in `agents/review/` and retrieve
       latest best practices from the knowledge base. Understand the project's signature style.
    2. **Design**: Create a `dspy.Signature` class that embodies the requested review rule.
    3. **Implement**:
       - Use `ClassVar` for metadata: `__agent_name__`, `__agent_category__`,
         `__agent_severity__`, `applicable_languages`.
       - Use standard `ReviewReport` and `ReviewFinding` from `agents.review.schema`.
       - Write a comprehensive docstring describing the scanning logic.

    ## Critical Guidelines:
    - **No placeholders**: Every field must be populated with a real, working technical description.
    - **YAGNI**: Don't add complexity unless strictly requested.
    - **Atomic**: Each agent should focus on ONE specific rule.

    ## REQUIRED CODE STRUCTURE:
    The generated code MUST follow this exact pattern. DO NOT include placeholder comments
    or "example" notes - generate COMPLETE, WORKING code:

    ```python
    from typing import ClassVar, List, Optional, Set

    import dspy
    from pydantic import Field

    from agents.review.schema import ReviewFinding, ReviewReport


    class YourCustomFinding(ReviewFinding):
        '''Custom finding with additional fields.
        Inherits: title, category, description, location, severity, suggestion.'''
        extra_detail: str = Field(..., description="Additional detail specific to this review type")


    class YourCustomReport(ReviewReport):
        '''Structured report for this specific review type.'''
        findings: List[YourCustomFinding] = Field(default_factory=list)
        extra_field: str = Field(..., description="Specific field for this review type")


    class YourClassName(dspy.Signature):
        '''
        Detailed docstring describing exactly what this reviewer checks for.
        Include specific rules, patterns, and what constitutes a violation.
        '''

        __agent_name__: ClassVar[str] = "Your-Agent-Name"  # Use hyphens, no spaces!
        __agent_category__: ClassVar[str] = "code-review"  # MUST be one from valid_categories input
        __agent_severity__: ClassVar[str] = "p2"  # p1, p2, or p3
        applicable_languages: ClassVar[Optional[Set[str]]] = {"python", "javascript"}

        code_diff: str = dspy.InputField(desc="The code changes to review")
        review_report: YourCustomReport = dspy.OutputField(desc="Structured review report")
    ```

    CRITICAL RULES:
    - The output field MUST be named `review_report` and use `dspy.OutputField`.
    - DO NOT include comments like "# Add custom fields here" or "placeholder".
    - Generate COMPLETE, production-ready code with real field definitions.
    - If creating a custom Finding class, it MUST inherit ReviewFinding.
      (ReviewFinding includes: title, category, description, severity, suggestion)
    """

    agent_description: str = dspy.InputField(
        desc="Description of what the review agent should check for"
    )
    existing_agents: str = dspy.InputField(desc="List of existing review agents for reference")
    valid_categories: str = dspy.InputField(
        desc="Comma-separated list of valid categories. __agent_category__ MUST be one of these."
    )

    file_name: str = dspy.OutputField(desc="Snake-case file name (e.g. sql_injection_reviewer.py)")
    class_name: str = dspy.OutputField(desc="CamelCase class name (e.g. SqlInjectionReviewer)")
    agent_name: str = dspy.OutputField(
        desc="Hyphenated name for CLI (e.g. SQL-Injection-Reviewer). NO SPACES - use hyphens!"
    )
    applicable_languages: List[str] = dspy.OutputField(
        desc="List of languages this agent applies to (e.g. ['python', 'javascript'])"
    )
    code_content = dspy.OutputField(
        desc="Full Python file content. MUST include: dspy.Signature class, "
        "review_report output field using dspy.OutputField, and proper imports."
    )
