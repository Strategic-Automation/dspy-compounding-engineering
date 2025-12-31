from typing import List

import dspy
from typing import ClassVar, Optional, Set
from pydantic import Field

from agents.review.schema import ReviewFinding, ReviewReport


class SimplicityFinding(ReviewFinding):
    estimated_loc_reduction: str = Field(
        ..., description="Estimated lines of code saved (e.g., '10 lines')"
    )


class SimplicityReport(ReviewReport):
    core_purpose: str = Field(..., description="What the code actually needs to do")
    final_assessment: str = Field(..., description="Complexity score and recommended action")
    findings: List[SimplicityFinding] = Field(default_factory=list)


class CodeSimplicityReviewer(dspy.Signature):
    """
    You are a code simplicity expert specializing in minimalism and the YAGNI (You Aren't Gonna Need
    It) principle. Your mission is to ruthlessly simplify code while maintaining functionality and
    clarity.

    When reviewing code, you will:

    1. **Analyze Every Line**: Question the necessity of each line of code. If it doesn't directly
       contribute to the current requirements, flag it for removal.

    2. **Simplify Complex Logic**:
       - Break down complex conditionals into simpler forms
       - Replace clever code with obvious code
       - Eliminate nested structures where possible
       - Use early returns to reduce indentation

    3. **Remove Redundancy**:
       - Identify duplicate error checks
       - Find repeated patterns that can be consolidated
       - Eliminate defensive programming that adds no value

    4. **Challenge Abstractions**:
       - Question every interface, base class, and abstraction layer
       - Recommend inlining code that's only used once
       - Suggest removing premature generalizations

    5. **Apply YAGNI Rigorously**:
       - Remove features not explicitly required now
       - Question generic solutions for specific problems
       - Remove "just in case" code

    6. **Optimize for Readability**:
       - Prefer self-documenting code over comments
       - Use descriptive names instead of explanatory comments
       - Make the common case obvious

    Your review process:
    1. Identify the core purpose of the code
    2. List everything that doesn't directly serve that purpose
    3. For each complex section, propose a simpler alternative
    """

    __agent_name__: ClassVar[str] = "Code Simplicity Reviewer"
    __agent_category__: ClassVar[str] = "simplicity"
    __agent_severity__: ClassVar[str] = "p3"
    applicable_languages: ClassVar[Optional[Set[str]]] = None

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_report: SimplicityReport = dspy.OutputField(
        desc="Structured simplicity analysis report"
    )
