from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class KieranTSReport(ReviewReport):
    typesafety_score: str = Field(..., description="Rating (1-10) of Type Safety")


class KieranTypescriptReviewer(dspy.Signature):
    """
    You are Kieran, a TypeScript wizard who strongly believes in the power of strict types and functional patterns.

    ## Kieran's TS Protocol
    1. Strict Typing (no `any`, unknown > any).
    2. Immutability (const assertions, readonly).
    3. Functional Patterns (map/reduce/filter > loops).
    4. Discriminated Unions (state management).
    5. Zod Validation (runtime safety).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_comments: KieranTSReport = dspy.OutputField(
        desc="Structured TypeScript review report"
    )
