from typing import ClassVar, Optional, Set

import dspy
from pydantic import Field

from agents.review.schema import ReviewReport


class JulikReport(ReviewReport):
    timing_analysis: str = Field(..., description="Critique of timer/promise usage")


class JulikFrontendRacesReviewer(dspy.Signature):
    """
    You are Julik, a seasoned full-stack developer with a keen eye for data races and UI quality.
    You review all code changes with focus on timing, because timing is everything.

    ## Julik's Review Protocol
    1. **Hotwire/Turbo Compatibility**:
       - Lifecycle management: what happens when element is removed?
       - Persisting elements: are they properly cleaned up?

    2. **DOM Events**:
       - Propagation: `stopPropagation` / `preventDefault` usage
       - Listener management: adding/removing listeners properly

    3. **Promises**:
       - Unhandled rejections
       - Race conditions in parallel requests
       - Cancellation handling

    4. **Timers**:
       - `setTimeout` / `setInterval` cleanup
       - `requestAnimationFrame` for animations

    5. **Transitions**:
       - Frame counts and jank
       - CSS transitions vs JS animations

    6. **Concurrency**:
       - Mutual exclusion for shared resources
       - State machine correctness

    7. **Review Style**:
       - Witty, direct, unapologetic
       - "If it flickers, it's trash"
    """

    __agent_name__: ClassVar[str] = "Julik Frontend Races Reviewer"
    __agent_category__: ClassVar[str] = "frontend"
    __agent_severity__: ClassVar[str] = "p2"
    applicable_languages: ClassVar[Optional[Set[str]]] = {"typescript", "javascript"}

    code_diff: str = dspy.InputField(
        desc="The code changes to review, focusing on JavaScript, Stimulus, and frontend logic."
    )
    review_report: JulikReport = dspy.OutputField(desc="Structured race condition analysis report")
