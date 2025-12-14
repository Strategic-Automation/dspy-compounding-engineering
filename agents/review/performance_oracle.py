from agents.review.schema import ReviewReport, ReviewFinding
from typing import List
from pydantic import Field
import dspy


class PerformanceFinding(ReviewFinding):
    estimated_impact: str = Field(
        ..., description="Estimated performance impact (High/Medium/Low)"
    )


class PerformanceReport(ReviewReport):
    scalability_assessment: str = Field(
        ..., description="Assessment of scalability implications"
    )
    optimization_opportunities: str = Field(
        ..., description="High-level optimization suggestions"
    )
    findings: List[PerformanceFinding] = Field(default_factory=list)


class PerformanceOracle(dspy.Signature):
    """
    You are a Performance Optimization Expert. You analyze code for inefficiencies, bottlenecks, and scalability issues.

    ## Performance Review Protocol
    1. Complexity Analysis (Big O, nested loops).
    2. Database Query Efficiency (N+1, missing indexes).
    3. Memory Management (leaks, large allocations).
    4. I/O Operations (blocking calls, network chatter).
    5. Caching Strategy (opportunities, invalidation).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    performance_analysis: PerformanceReport = dspy.OutputField(
        desc="Structured performance analysis report"
    )
