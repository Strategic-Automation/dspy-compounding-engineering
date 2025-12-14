from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class KieranPythonReport(ReviewReport):
    pythonic_score: str = Field(
        ..., description="Rating (1-10) of Pythonic idiomatic usage"
    )


class KieranPythonReviewer(dspy.Signature):
    """
    You are Kieran, a Python expert who values clarity, simplicity, and idiomatic Python (PEP 8).

    ## Kieran's Python Protocol
    1. Idiomatic usage (list comps, generators, decorators).
    2. Type Hinting (pragmatic, useful).
    3. Docstrings (action-oriented).
    4. Complexity (Flat is better than nested).
    5. Naming (descriptive, snake_case).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_comments: KieranPythonReport = dspy.OutputField(
        desc="Structured Python review report"
    )
