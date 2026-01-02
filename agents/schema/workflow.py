from typing import List

from pydantic import Field

from agents.schema.base import BaseResearchReport


class PlanReport(BaseResearchReport):
    """Structured report for a feature implementation or bug fix plan."""

    overview: str = Field(..., description="High-level description of the plan")
    problem_statement: str = Field(..., description="Why this change matters")
    proposed_solution: str = Field(..., description="High-level implementation approach")
    technical_considerations: List[str] = Field(
        default_factory=list, description="Architecture, performance, security, and etc."
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="List of requirements that must be met"
    )
    implementation_steps: List[str] = Field(
        default_factory=list, description="Step-by-step tasks for implementation"
    )
