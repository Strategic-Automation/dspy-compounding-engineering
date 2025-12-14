from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class DataIntegrityReport(ReviewReport):
    migration_analysis: str = Field(
        ..., description="Assessment of database migration safety"
    )
    privacy_compliance: str = Field(..., description="GDPR/Privacy compliance check")
    rollout_strategy: str = Field(
        ..., description="Safe rollout/rollback recommendations"
    )


class DataIntegrityGuardian(dspy.Signature):
    """
    You are a Data Integrity Guardian, an expert in database design, data migration safety, and data governance.

    ## Integrity Review Protocol
    1. Analyze Database Migrations (reversibility, locking).
    2. Validate Data Constraints (validations, foreign keys).
    3. Review Transaction Boundaries (atomicity, isolation).
    4. Preserve Referential Integrity (cascades, orphans).
    5. Ensure Privacy Compliance (PII, encryption).
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    data_integrity_report: DataIntegrityReport = dspy.OutputField(
        desc="Structured data integrity analysis report"
    )
