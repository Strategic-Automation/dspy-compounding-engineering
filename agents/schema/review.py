from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    title: str = Field(..., description="Concise title of the finding")
    category: str = Field(..., description="Category of the issue")
    description: str = Field(..., description="Detailed explanation")
    location: Optional[str] = Field(None, description="File and line number if applicable")
    severity: str = Field(..., description="Severity or Priority (e.g. Critical, High, Medium, Low)")
    suggestion: str = Field(..., description="Actionable suggestion or fix")


class ReviewReport(BaseModel):
    summary: str = Field(..., description="High-level assessment summary")
    findings: List[ReviewFinding] = Field(default_factory=list)
    analysis: str = Field(..., description="Detailed analysis, risk assessment, or additional context")
    action_required: bool = Field(..., description="True if actionable findings are present")
