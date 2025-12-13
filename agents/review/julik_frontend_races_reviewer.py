from typing import List
from pydantic import BaseModel, Field
import dspy


class RaceFinding(BaseModel):
    title: str = Field(..., description="Concise title of the race/timing issue")
    category: str = Field(
        ..., description="Hotwire, Timer, Promise, Event, or Transition"
    )
    description: str = Field(
        ..., description="Witty description of the potential race condition"
    )
    location: str = Field(..., description="File and line number")
    recommendation: str = Field(
        ..., description="Specific fix (e.g., cancellation token, state machine)"
    )


class JulikReport(BaseModel):
    summary: str = Field(
        ..., description="High-level assessment in Julik's witty voice"
    )
    findings: List[RaceFinding] = Field(
        default_factory=list, description="List of race condition findings"
    )
    timing_analysis: str = Field(..., description="Critique of timer/promise usage")
    action_required: bool = Field(
        ..., description="True if race conditions or timing issues found"
    )


class JulikFrontendRacesReviewer(dspy.Signature):
    """
    You are Julik, a seasoned full-stack developer with a keen eye for data races and UI quality.
    You review all code changes with focus on timing, because timing is everything.

    ## Julik's Review Protocol
    1. Hotwire/Turbo Compatibility (lifecycle, unmounting).
    2. DOM Events (propagation, listener management).
    3. Promises (unhandled rejections, cancellation).
    4. Timers (cancellation tokens, cleanup).
    5. Transitions (frame counts, jank).
    6. Concurrency (mutual exclusion, state machines).
    7. Review Style (witty, direct, unapologetic).
    """

    code_diff: str = dspy.InputField(
        desc="The code changes to review, focusing on JavaScript, Stimulus, and frontend logic."
    )
    race_condition_analysis: JulikReport = dspy.OutputField(
        desc="Structured race condition analysis report"
    )
