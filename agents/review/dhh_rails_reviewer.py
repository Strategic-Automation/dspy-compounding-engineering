from typing import List
from pydantic import BaseModel, Field
import dspy


class RailsFinding(BaseModel):
    title: str = Field(..., description="Concise title of the Rails violation")
    violation_type: str = Field(
        ..., description="Convention Violation, Complexity, or Anti-Pattern"
    )
    description: str = Field(..., description="Description of the issue in DHH's voice")
    location: str = Field(..., description="File and line number")
    recommendation: str = Field(..., description="The Rails Way alternative")


class DhhReviewReport(BaseModel):
    summary: str = Field(..., description="Overall assessment in DHH's voice")
    findings: List[RailsFinding] = Field(
        default_factory=list, description="List of violations found"
    )
    complexity_analysis: str = Field(
        ..., description="Critique of unnecessary abstractions"
    )
    final_verdict: str = Field(
        ..., description="Final judgment (Pass/Fail) with witty remark"
    )
    action_required: bool = Field(..., description="True if violations present")


class DhhRailsReviewer(dspy.Signature):
    """
    You are David Heinemeier Hansson, creator of Ruby on Rails.
    You review code with zero tolerance for unnecessary complexity or deviation from Rails conventions.

    ## DHH Review Protocol
    1. Rails Convention Adherence (omakase, fat models).
    2. Pattern Recognition (reject React/JS creep, microservices).
    3. Complexity Analysis (tear apart service objects/presenters).
    4. Review Style (direct, unforgiving, champion simplicity).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    dhh_review: DhhReviewReport = dspy.OutputField(
        desc="Structured Rails review report in DHH's voice"
    )
