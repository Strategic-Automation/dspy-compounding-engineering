from typing import List
from pydantic import BaseModel, Field
import dspy


class ArchitectureFinding(BaseModel):
    title: str = Field(..., description="Concise title of the architectural issue")
    category: str = Field(
        ..., description="e.g., Coupling, Abstraction, SOLID, Dependencies"
    )
    description: str = Field(..., description="Detailed description of the finding")
    impact: str = Field(
        ..., description="Impact on system evolution and maintainability"
    )
    recommendation: str = Field(..., description="Specific suggestion for improvement")


class ArchitectureReport(BaseModel):
    architecture_overview: str = Field(
        ..., description="Brief summary of relevant architectural context"
    )
    change_assessment: str = Field(
        ..., description="How changes fit within existing architecture"
    )
    findings: List[ArchitectureFinding] = Field(
        default_factory=list, description="List of architectural findings"
    )
    risk_analysis: str = Field(
        ..., description="Potential architectural risks or technical debt"
    )
    action_required: bool = Field(
        ..., description="True if actionable findings present"
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
