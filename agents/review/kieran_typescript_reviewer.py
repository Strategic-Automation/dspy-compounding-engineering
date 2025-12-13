from typing import List
from pydantic import BaseModel, Field
import dspy


class KieranTSFinding(BaseModel):
    title: str = Field(..., description="Concise title of the finding")
    category: str = Field(..., description="Type Safety, Naming, Pattern, or Module")
    description: str = Field(
        ..., description="Detailed explanation of why this is an issue"
    )
    location: str = Field(..., description="File and line number")
    suggestion: str = Field(..., description="Specific improvement with example")


class KieranTSReport(BaseModel):
    summary: str = Field(..., description="High-level assessment of the changes")
    findings: List[KieranTSFinding] = Field(
        default_factory=list, description="List of findings"
    )
    typesafety_score: str = Field(..., description="Rating (1-10) of Type Safety")
    action_required: bool = Field(
        ..., description="True if actionable findings present"
    )


class KieranTypescriptReviewer(dspy.Signature):
    """
    You are Kieran, a super senior TypeScript developer with an exceptionally high bar for code quality.

    ## Kieran's TypeScript Review Protocol
    1. Type Safety (No 'any', strict null checks).
    2. Naming & Clarity (5-second rule).
    3. Testing (Testable > Clever).
    4. Module Extraction (Complex logic -> New Module).
    5. Modern Patterns (ES6+, functional).
    6. Philosophy (Duplication > Complexity, Simple > DRY).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_comments: KieranTSReport = dspy.OutputField(
        desc="Structured TypeScript review report"
    )
