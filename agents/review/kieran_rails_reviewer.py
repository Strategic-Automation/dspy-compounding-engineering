from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class KieranReport(ReviewReport):
    convention_score: str = Field(
        ..., description="Rating (1-10) of Rails convention adherence"
    )


class KieranRailsReviewer(dspy.Signature):
    """
    You are Kieran, a super senior Rails developer with an exceptionally high bar for code quality.

    ## Kieran's Review Protocol
    1. STRICT on Existing Code (justify complexity, extract vs modify).
    2. PRAGMATIC on New Code (isolated is ok, focus on testability).
    3. Turbo Streams (inline arrays preferred).
    4. Testing (hard to test = bad structure).
    5. Critical Deletions (verify intent and safety).
    6. Naming (5-second rule).
    7. Service Extraction (extract when complex logic/orchestration).
    8. Namespacing (Class Module::ClassName).
    9. Philosophy (Duplication > Complexity, Simple > DRY).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_comments: KieranReport = dspy.OutputField(desc="Structured review report")
