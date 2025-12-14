from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class ArchitectureReport(ReviewReport):
    risk_analysis: str = Field(
        ..., description="Potential architectural risks or technical debt"
    )


class ArchitectureStrategist(dspy.Signature):
    """
    You are a System Architecture Expert specializing in analyzing code changes and system design decisions.

    ## Architecture Analysis Protocol
    1. Understand System Architecture (structure, patterns).
    2. Analyze Change Context (fit, boundaries).
    3. Identify Violations (SOLID, coupling, abstraction).
    4. Consider Long-term Implications (scalability, maintainability).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    architecture_analysis: ArchitectureReport = dspy.OutputField(
        desc="Structured architectural analysis report"
    )
