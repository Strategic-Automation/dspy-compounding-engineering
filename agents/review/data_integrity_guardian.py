from typing import List
from pydantic import BaseModel, Field
import dspy


class IntegrityFinding(BaseModel):
    title: str = Field(..., description="Concise title of the integrity issue")
    risk_type: str = Field(
        ..., description="Migration Safety, Data Loss, Constraints, or Privacy"
    )
    description: str = Field(..., description="Detailed description of the finding")
    impact: str = Field(..., description="Potential impact on data integrity")
    prevention: str = Field(..., description="How to prevent or fix this issue")


class DataIntegrityReport(BaseModel):
    migration_analysis: str = Field(
        ..., description="Assessment of database migration safety"
    )
    privacy_compliance: str = Field(..., description="GDPR/Privacy compliance check")
    findings: List[IntegrityFinding] = Field(
        default_factory=list, description="List of integrity findings"
    )
    rollout_strategy: str = Field(
        ..., description="Safe rollout/rollback recommendations"
    )
    action_required: bool = Field(
        ..., description="True if actionable findings present"
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
