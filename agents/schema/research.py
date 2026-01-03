from typing import List, Optional

from pydantic import Field

from agents.schema.base import BaseResearchReport


class FrameworkDocsReport(BaseResearchReport):
    """Structured report for framework and library documentation research."""

    version_information: Optional[str] = Field(
        None, description="Current version and any relevant constraints"
    )


class BestPracticesReport(BaseResearchReport):
    """Structured report for best practices research."""

    implementation_patterns: List[str] = Field(
        default_factory=list, description="Recommended architectural or code patterns"
    )
    anti_patterns: List[str] = Field(
        default_factory=list, description="Patterns or practices to avoid"
    )


class RepoResearchReport(BaseResearchReport):
    """Structured report for repository-wide research and analysis."""

    architecture_overview: Optional[str] = Field(
        None, description="High-level architecture assessment"
    )


class GitHistoryReport(BaseResearchReport):
    """Structured report for git history and repository evolution analysis."""

    evolution_summary: Optional[str] = Field(
        None, description="Summary of how the project evolved over time"
    )
