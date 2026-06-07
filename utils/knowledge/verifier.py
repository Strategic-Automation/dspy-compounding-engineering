"""
Knowledge Base Verification Module.

Ensures that the AI.md file and the Knowledge Base (JSON + SQLite + Vector DB)
are always in sync with the codebase. Provides verification that KB contents
are consistent and alerts if the KB needs regeneration.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class VerificationFinding:
    """A single finding from the KB verification."""

    severity: str  # "info", "warning", "error"
    category: str  # "json", "db", "orphan", "ai_md"
    message: str
    details: Optional[str] = None


@dataclass
class VerificationReport:
    """Summary report of the KB verification."""

    status: str  # "healthy", "degraded", "critical"
    findings: List[VerificationFinding] = field(default_factory=list)
    timestamp: str = ""
    summary: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class KnowledgeBaseVerifier:
    """
    Verifies consistency between the Knowledge Base components:
    - JSON learning files in .knowledge/
    - SQLite knowledge.db database
    - AI.md documentation file

    Usage:
        verifier = KnowledgeBaseVerifier(knowledge_dir="/path/to/.knowledge")
        report = verifier.verify()
    """

    def __init__(self, knowledge_dir: str):
        """
        Initialize the verifier.

        Args:
            knowledge_dir: Path to the .knowledge directory containing
                           JSON files, knowledge.db, and AI.md.
        """
        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self.db_path = os.path.join(self.knowledge_dir, "knowledge.db")
        self.ai_md_path = os.path.join(self.knowledge_dir, "AI.md")

    def verify(self) -> VerificationReport:
        """
        Run all verification checks and return a report.

        Returns:
            VerificationReport with status and findings.
        """
        findings: List[VerificationFinding] = []

        # 1. Check JSON learnings validity
        findings.extend(self._check_json_files())

        # 2. Check DB consistency with JSON files
        findings.extend(self._check_db_consistency())

        # 3. Check AI.md consistency
        findings.extend(self._check_ai_md_consistency())

        # Determine overall status
        status = self._determine_status(findings)

        # Build summary
        summary = self._build_summary(findings)

        return VerificationReport(
            status=status,
            findings=findings,
            summary=summary,
        )

    def _check_json_files(self) -> List[VerificationFinding]:
        """
        Check that all .knowledge/ JSON learning files are valid and parseable.

        Scans for .json files (excluding backups/, archive/, etc.) and verifies
        each is valid JSON with required fields.
        """
        findings: List[VerificationFinding] = []
        excluded_dirs = {"backups", "archive", "__pycache__"}

        if not os.path.isdir(self.knowledge_dir):
            findings.append(
                VerificationFinding(
                    severity="error",
                    category="json",
                    message="Knowledge directory does not exist",
                    details=self.knowledge_dir,
                )
            )
            return findings

        json_files_found = 0
        invalid_count = 0

        for entry in os.listdir(self.knowledge_dir):
            if entry.endswith(".json"):
                json_files_found += 1
                filepath = os.path.join(self.knowledge_dir, entry)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Basic validation: must have an 'id' or at least be a dict
                    if not isinstance(data, dict):
                        findings.append(
                            VerificationFinding(
                                severity="warning",
                                category="json",
                                message=f"JSON file is not a dictionary: {entry}",
                            )
                        )
                except json.JSONDecodeError as e:
                    invalid_count += 1
                    findings.append(
                        VerificationFinding(
                            severity="error",
                            category="json",
                            message=f"Invalid JSON file: {entry}",
                            details=str(e),
                        )
                    )
                except (OSError, UnicodeDecodeError) as e:
                    invalid_count += 1
                    findings.append(
                        VerificationFinding(
                            severity="error",
                            category="json",
                            message=f"Cannot read JSON file: {entry}",
                            details=str(e),
                        )
                    )

        if json_files_found == 0:
            findings.append(
                VerificationFinding(
                    severity="info",
                    category="json",
                    message="No JSON learning files found in knowledge directory",
                )
            )
        elif invalid_count == 0:
            findings.append(
                VerificationFinding(
                    severity="info",
                    category="json",
                    message=f"All {json_files_found} JSON files are valid and parseable",
                )
            )

        return findings

    def _check_db_consistency(self) -> List[VerificationFinding]:
        """
        Check that the SQLite database is consistent with JSON files.

        Reports:
        - Orphaned JSON files (JSON with no corresponding DB entry)
        - Orphaned DB entries (DB entry with no corresponding JSON file)
        - Database integrity issues
        """
        findings: List[VerificationFinding] = []

        if not os.path.exists(self.db_path):
            findings.append(
                VerificationFinding(
                    severity="warning",
                    category="db",
                    message="SQLite database file does not exist",
                    details=self.db_path,
                )
            )
            return findings

        # Get DB entry IDs
        try:
            db_ids = set()
            with sqlite3.connect(self.db_path) as conn:
                # Verify table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='learnings'"
                )
                if cursor.fetchone() is None:
                    findings.append(
                        VerificationFinding(
                            severity="error",
                            category="db",
                            message="Database exists but 'learnings' table is missing",
                        )
                    )
                    return findings

                cursor = conn.execute("SELECT id FROM learnings")
                db_ids = {row[0] for row in cursor.fetchall()}
        except sqlite3.DatabaseError as e:
            findings.append(
                VerificationFinding(
                    severity="error",
                    category="db",
                    message="Database integrity check failed",
                    details=str(e),
                )
            )
            return findings

        # Get JSON file IDs
        json_ids = set()
        json_id_to_file: Dict[str, str] = {}
        for entry in os.listdir(self.knowledge_dir):
            if entry.endswith(".json"):
                filepath = os.path.join(self.knowledge_dir, entry)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "id" in data:
                        json_ids.add(data["id"])
                        json_id_to_file[data["id"]] = entry
                except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                    pass  # Already reported in JSON check

        total_db = len(db_ids)
        total_json = len(json_ids)
        overlapping = db_ids & json_ids

        # Find orphaned JSON files (in JSON but not in DB)
        orphaned_json = json_ids - db_ids
        if orphaned_json:
            for oid in sorted(orphaned_json):
                findings.append(
                    VerificationFinding(
                        severity="warning",
                        category="orphan",
                        message=f"Orphaned JSON file (no DB entry): {json_id_to_file.get(oid, 'unknown')}",
                        details=f"Learning ID: {oid}",
                    )
                )

        # Find orphaned DB entries (in DB but not in JSON)
        orphaned_db = db_ids - json_ids
        if orphaned_db:
            for oid in sorted(orphaned_db):
                findings.append(
                    VerificationFinding(
                        severity="warning",
                        category="orphan",
                        message="Orphaned DB entry (no JSON file)",
                        details=f"Learning ID: {oid}",
                    )
                )

        findings.append(
            VerificationFinding(
                severity="info",
                category="db",
                message=f"DB-JSON sync: {len(overlapping)} synchronized, "
                f"{len(orphaned_json)} orphaned JSON, {len(orphaned_db)} orphaned DB",
                details=f"Total DB entries: {total_db}, Total JSON files: {total_json}",
            )
        )

        return findings

    def _check_ai_md_consistency(self) -> List[VerificationFinding]:
        """
        Check that AI.md size and content are consistent with the learnings.

        Verifies:
        - AI.md exists
        - AI.md has non-zero size
        - AI.md content includes section headers that should be present based on categories
        """
        findings: List[VerificationFinding] = []

        if not os.path.exists(self.ai_md_path):
            findings.append(
                VerificationFinding(
                    severity="warning",
                    category="ai_md",
                    message="AI.md file does not exist",
                    details=self.ai_md_path,
                )
            )
            return findings

        try:
            with open(self.ai_md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            findings.append(
                VerificationFinding(
                    severity="error",
                    category="ai_md",
                    message="Cannot read AI.md file",
                    details=str(e),
                )
            )
            return findings

        ai_md_size = len(content)
        findings.append(
            VerificationFinding(
                severity="info",
                category="ai_md",
                message=f"AI.md size: {ai_md_size:,} characters",
            )
        )

        if ai_md_size == 0:
            findings.append(
                VerificationFinding(
                    severity="warning",
                    category="ai_md",
                    message="AI.md exists but is empty",
                )
            )
            return findings

        # Check if AI.md has the expected header
        if "# AI Knowledge Base" not in content and len(content) > 100:
            findings.append(
                VerificationFinding(
                    severity="warning",
                    category="ai_md",
                    message="AI.md does not contain expected header '# AI Knowledge Base'",
                    details="File may have been manually edited or corrupted",
                )
            )

        # Cross-reference: check if categories in DB are represented in AI.md
        categories_in_kb = set()
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT DISTINCT category FROM learnings")
                    categories_in_kb = {row[0].title() for row in cursor.fetchall()}
            except sqlite3.DatabaseError:
                pass

        if categories_in_kb:
            missing_categories = []
            for cat in categories_in_kb:
                if f"## {cat}" not in content:
                    missing_categories.append(cat)

            if missing_categories:
                findings.append(
                    VerificationFinding(
                        severity="warning",
                        category="ai_md",
                        message=f"AI.md is missing sections for {len(missing_categories)} category(ies)",
                        details=f"Missing categories: {', '.join(sorted(missing_categories))}",
                    )
                )
            else:
                findings.append(
                    VerificationFinding(
                        severity="info",
                        category="ai_md",
                        message=f"All {len(categories_in_kb)} KB category(ies) are represented in AI.md",
                    )
                )

        return findings

    def _determine_status(self, findings: List[VerificationFinding]) -> str:
        """
        Determine overall health status from findings.

        Returns:
            "healthy" - no errors or warnings
            "degraded" - has warnings but no errors
            "critical" - has one or more errors
        """
        if not findings:
            return "healthy"

        has_errors = any(f.severity == "error" for f in findings)
        has_warnings = any(f.severity == "warning" for f in findings)

        if has_errors:
            return "critical"
        elif has_warnings:
            return "degraded"
        else:
            return "healthy"

    def _build_summary(self, findings: List[VerificationFinding]) -> Dict[str, Any]:
        """Build a summary dictionary from findings."""
        return {
            "total_findings": len(findings),
            "error_count": sum(1 for f in findings if f.severity == "error"),
            "warning_count": sum(1 for f in findings if f.severity == "warning"),
            "info_count": sum(1 for f in findings if f.severity == "info"),
        }


def format_report(report: VerificationReport) -> str:
    """Format a VerificationReport for human-readable display."""
    status_colors = {
        "healthy": "green",
        "degraded": "yellow",
        "critical": "red",
    }
    severity_icons = {
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
    }

    lines = []
    color = status_colors.get(report.status, "white")
    lines.append(f"[{color}]KB Verification Report: {report.status.upper()}[/{color}]")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append("")

    if report.summary:
        lines.append(f"Total findings: {report.summary['total_findings']}")
        lines.append(f"  Errors:   {report.summary['error_count']}")
        lines.append(f"  Warnings: {report.summary['warning_count']}")
        lines.append(f"  Info:     {report.summary['info_count']}")
        lines.append("")

    for finding in report.findings:
        icon = severity_icons.get(finding.severity, "•")
        line = f"{icon} [{finding.severity.upper()}] ({finding.category}) {finding.message}"
        if finding.details:
            line += f"\n    {finding.details}"
        lines.append(line)

    return "\n".join(lines)
