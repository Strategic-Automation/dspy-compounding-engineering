from typing import List, Optional

from pydantic import BaseModel, Field


class ResearchInsight(BaseModel):
    """Standardized model for a single research discovery or insight."""

    title: str = Field(..., description="Concise title of the insight")
    category: str = Field(..., description="Category (e.g. Architecture, API, Security, Pattern)")
    description: str = Field(..., description="Detailed explanation of the discovery")
    recommendation: Optional[str] = Field(
        None, description="Actionable recommendation based on the insight"
    )
    source: Optional[str] = Field(
        None, description="Source of the discovery (file, URL, or commit)"
    )


class BaseResearchReport(BaseModel):
    """Base class for all research reports to ensure field consistency."""

    summary: str = Field(..., description="High-level assessment summary")
    analysis: str = Field(..., description="Detailed synthesis and technical implications")
    insights: List[ResearchInsight] = Field(
        default_factory=list, description="Categorized research discoveries"
    )
    references: List[str] = Field(
        default_factory=list, description="Links to docs, source files, or issues"
    )

    def format_markdown(self) -> str:
        """Formats the report as a clean markdown string."""
        lines = [
            f"### Summary\n{self.summary}\n",
            f"### Analysis\n{self.analysis}\n",
        ]

        # Dynamically include specialized fields
        base_fields = {"summary", "analysis", "insights", "references"}
        for field_name, value in self.dict().items():
            if field_name not in base_fields and value:
                title = field_name.replace("_", " ").title()
                if isinstance(value, list):
                    lines.append(f"### {title}")
                    for item in value:
                        lines.append(f"- {item}")
                    lines.append("")
                else:
                    lines.append(f"### {title}\n{value}\n")

        self._format_insights(lines)
        self._format_references(lines)

        return "\n".join(lines)

    def _format_insights(self, lines: list) -> None:
        """Helper to format insights section."""
        if self.insights:
            lines.append("### Key Insights")
            for insight in self.insights:
                lines.append(f"- **{insight.title}** ({insight.category})")
                lines.append(f"  {insight.description}")
                if insight.recommendation:
                    lines.append(f"  *Recommendation:* {insight.recommendation}")
                if insight.source:
                    lines.append(f"  *Source:* {insight.source}")
            lines.append("")

    def _format_references(self, lines: list) -> None:
        """Helper to format references section."""
        if self.references:
            lines.append("### References")
            for ref in self.references:
                lines.append(f"- {ref}")
            lines.append("")


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
