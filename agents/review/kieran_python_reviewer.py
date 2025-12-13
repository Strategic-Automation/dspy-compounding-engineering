from typing import List
from pydantic import BaseModel, Field
import dspy


class KieranPythonFinding(BaseModel):
    title: str = Field(..., description="Concise title of the finding")
    category: str = Field(..., description="Type Hints, Naming, Pattern, or Import")
    description: str = Field(
        ..., description="Detailed explanation of why this is an issue"
    )
    location: str = Field(..., description="File and line number")
    suggestion: str = Field(..., description="Specific improvement with example")


class KieranPythonReport(BaseModel):
    summary: str = Field(..., description="High-level assessment of the changes")
    findings: List[KieranPythonFinding] = Field(
        default_factory=list, description="List of findings"
    )
    pythonic_score: str = Field(
        ..., description="Rating (1-10) of Pythonic code quality"
    )
    action_required: bool = Field(
        ..., description="True if actionable findings present"
    )


class KieranPythonReviewer(dspy.Signature):
    """
    You are Kieran, a super senior Python developer with an exceptionally high bar for code quality.

    ## Kieran's Python Review Protocol
    1. Type Hints (Strict typing, modern syntax).
    2. Naming & Clarity (5-second rule, descriptive).
    3. Pythonic Patterns (context managers, comprehensions).
    4. Import Organization (PEP 8, absolute imports).
    5. Modern Features (f-strings, pattern matching).
    6. Simplicity (Explicit > Implicit, Duplication > Complexity).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_comments: KieranPythonReport = dspy.OutputField(
        desc="Structured Python review report"
    )
