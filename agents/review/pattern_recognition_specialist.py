from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class PatternReport(ReviewReport):
    naming_convention_analysis: str = Field(..., description="Analysis of naming patterns")
    duplication_metrics: str = Field(..., description="Assessment of code duplication")


class PatternRecognitionSpecialist(dspy.Signature):
    """
    You are a Pattern Recognition Specialist. You verify that code changes follow established project patterns and idioms.

    ## Pattern Review Protocol
    1. Verify Consistency (style, folder structure).
    2. Detect Anti-Patterns (God objects, magic numbers).
    3. Enforce Naming Conventions.
    4. Check for Duplication (DRY).
    5. Identify Missing Abstractions.
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    pattern_analysis: PatternReport = dspy.OutputField(
        desc="Structured pattern analysis report"
    )
