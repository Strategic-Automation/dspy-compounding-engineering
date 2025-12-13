from typing import List
from pydantic import BaseModel, Field
import dspy


class SimplicityFinding(BaseModel):
    issue_type: str = Field(
        ..., description="Complexity, Redundancy, YAGNI, or Abstraction"
    )
    description: str = Field(
        ..., description="Description of the unnecessary complexity"
    )
    location: str = Field(..., description="File and line numbers")
    recommendation: str = Field(..., description="Simpler alternative implementation")
    estimated_loc_reduction: str = Field(
        ..., description="Estimated lines of code saved (e.g., '10 lines')"
    )


class SimplicityReport(BaseModel):
    core_purpose: str = Field(..., description="What the code actually needs to do")
    assessment_summary: str = Field(
        ..., description="Overall assessment of code simplicity"
    )
    findings: List[SimplicityFinding] = Field(
        default_factory=list, description="List of simplification opportunities"
    )
    final_assessment: str = Field(
        ..., description="Complexity score and recommended action"
    )
    action_required: bool = Field(
        ..., description="True if simplification opportunities found"
    )


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
