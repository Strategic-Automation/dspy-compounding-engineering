from agents.review.schema import ReviewReport, ReviewFinding
from typing import List
from pydantic import Field
import dspy


class SimplicityFinding(ReviewFinding):
    estimated_loc_reduction: str = Field(
        ..., description="Estimated lines of code saved (e.g., '10 lines')"
    )


class SimplicityReport(ReviewReport):
    core_purpose: str = Field(..., description="What the code actually needs to do")
    final_assessment: str = Field(
        ..., description="Complexity score and recommended action"
    )
    findings: List[SimplicityFinding] = Field(default_factory=list)


class CodeSimplicityReviewer(dspy.Signature):
    """
    You are a code simplicity expert specializing in minimalism and the YAGNI principle.
    Your mission is to ruthlessly simplify code while maintaining functionality.

    ## Simplicity Review Protocol
    1. Analyze Every Line (question necessity).
    2. Simplify Complex Logic (conditionals, nesting).
    3. Remove Redundancy (duplicates, dead code).
    4. Challenge Abstractions (YAGNI, over-engineering).
    5. Optimize for Readability (naming, clarity).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    simplification_analysis: SimplicityReport = dspy.OutputField(
        desc="Structured simplicity analysis report"
    )
