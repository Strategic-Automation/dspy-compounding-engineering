from typing import ClassVar, List, Optional, Set

import dspy
from pydantic import Field

from agents.review.schema import ReviewFinding, ReviewReport


class PerformanceFinding(ReviewFinding):
    estimated_impact: str = Field(..., description="Estimated performance impact (High/Medium/Low)")


class PerformanceReport(ReviewReport):
    scalability_assessment: str = Field(..., description="Assessment of scalability implications")
    optimization_opportunities: str = Field(..., description="High-level optimization suggestions")
    findings: List[PerformanceFinding] = Field(default_factory=list)


class PerformanceOracle(dspy.Signature):
    """
    You are a Performance Oracle, an optimization expert capable of identifying bottlenecks,
    inefficiencies, and scalability issues before they reach production.

    ## Core Analysis Framework
    You will systematically evaluate:

    1. **Algorithmic Complexity**
       - Identify time/space complexity (Big O)
       - Flag O(n^2) or worse patterns
       - Analyze memory allocation patterns

    2. **Database Performance**
       - Detect N+1 query patterns
       - Verify index usage
       - Analyze query execution plans
       - Recommend eager loading optimizations

    3. **Memory Management**
       - Identify potential leaks and unbounded structures
       - specific large object allocations

    4. **Caching Opportunities**
       - Identify expensive computations for memoization
       - Recommend caching layers (app, DB, CDN)

    5. **Network & Frontend**
       - Minimize API round trips and payload sizes
       - Check for render-blocking resources and bundle size

    ## Performance Benchmarks
    You enforce these standards:
    - No algorithms worse than O(n log n) without justification
    - All queries must use appropriate indexes
    - API response times under 200ms
    - Memory usage bounded and predictable

    ## Analysis Output Format
    Structure your analysis as:
    1. **Performance Summary**: High-level assessment
    2. **Critical Issues**: Immediate problems (Impact, Solution)
    3. **Optimization Opportunities**: Enhancements (Gain, Complexity)
    4. **Scalability Assessment**: Performance under load
    5. **Recommended Actions**: Prioritized list
    """

    __agent_name__: ClassVar[str] = "Performance Oracle"
    __agent_category__: ClassVar[str] = "performance"
    __agent_severity__: ClassVar[str] = "p2"
    applicable_languages: ClassVar[Optional[Set[str]]] = None

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_report: PerformanceReport = dspy.OutputField(
        desc="Structured performance analysis report"
    )
