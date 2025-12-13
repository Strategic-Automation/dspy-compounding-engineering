from typing import List
from pydantic import BaseModel, Field
import dspy


class PatternFinding(BaseModel):
    title: str = Field(..., description="Name of the pattern or anti-pattern")
    type: str = Field(..., description="Design Pattern or Anti-Pattern")
    description: str = Field(..., description="Description of usage")
    location: str = Field(..., description="File and line number")
    recommendation: str = Field(
        ..., description="Recommendation (keep, refactor, remove)"
    )


class PatternReport(BaseModel):
    summary: str = Field(..., description="High-level pattern usage assessment")
    findings: List[PatternFinding] = Field(
        default_factory=list, description="List of patterns and anti-patterns found"
    )
    naming_convention_analysis: str = Field(
        ..., description="Assessment of naming consistency"
    )
    duplication_metrics: str = Field(..., description="Assessment of code duplication")
    action_required: bool = Field(
        ..., description="True if actionable findings (anti-patterns) present"
    )


class PatternRecognitionSpecialist(dspy.Signature):
    """
    You are a Code Pattern Analysis Expert specializing in identifying design patterns, anti-patterns, and code quality issues.

    ## Pattern Analysis Protocol
    1. Design Pattern Detection (Factory, Singleton, etc).
    2. Anti-Pattern Identification (God objects, spaghetti code).
    3. Naming Convention Analysis (consistency, clarity).
    4. Code Duplication Detection (DRY violations).
    5. Architectural Boundary Review (layer violations).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    pattern_analysis: PatternReport = dspy.OutputField(
        desc="Structured pattern analysis report"
    )
