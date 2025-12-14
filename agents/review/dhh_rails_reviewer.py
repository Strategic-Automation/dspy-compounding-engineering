from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class DhhReviewReport(ReviewReport):
    complexity_analysis: str = Field(
        ..., description="Critique of unnecessary abstractions"
    )
    final_verdict: str = Field(
        ..., description="Final judgment (Pass/Fail) with witty remark"
    )


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
