from typing import List
from pydantic import BaseModel, Field
import dspy


class PerformanceFinding(BaseModel):
    title: str = Field(..., description="Concise title of the performance issue")
    category: str = Field(..., description="Algorithmic, Database, Memory, or Caching")
    description: str = Field(..., description="Detailed description of the finding")
    impact: str = Field(
        ..., description="Latency, resource usage, or scalability impact"
    )
    recommendation: str = Field(..., description="Specific optimization advice")


class PerformanceReport(BaseModel):
    summary: str = Field(..., description="High-level performance assessment")
    scalability_assessment: str = Field(
        ..., description="Projected performance at scale"
    )
    findings: List[PerformanceFinding] = Field(
        default_factory=list, description="List of performance findings"
    )
    optimization_opportunities: str = Field(
        ..., description="Areas for future optimization"
    )
    action_required: bool = Field(
        ..., description="True if actionable findings present"
    )


class PerformanceOracle(dspy.Signature):
    """
    You are the Performance Oracle, an elite performance optimization expert specializing in identifying and resolving performance bottlenecks.

    ## Performance Analysis Protocol
    1. Algorithmic Complexity (Big O, loops).
    2. Database Performance (N+1, indexes).
    3. Memory Management (leaks, allocations).
    4. Caching Opportunities (memoization).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    performance_analysis: PerformanceReport = dspy.OutputField(
        desc="Structured performance analysis report"
    )
