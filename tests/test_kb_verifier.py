"""Tests for Knowledge Base verification functionality."""

import json
import sqlite3

import pytest

from utils.knowledge.verifier import (
    KnowledgeBaseVerifier,
    VerificationFinding,
    VerificationReport,
    format_report,
)


def _create_test_kb(temp_dir, learnings=None, ai_md_content=None, json_files=None):
    """Helper to create a test knowledge directory.

    Args:
        temp_dir: Path to a temp directory.
        learnings: List of dicts to insert into the SQLite DB.
        ai_md_content: String content for AI.md (if None, not created).
        json_files: Dict mapping filename -> dict content for JSON files.
    """
    kb_dir = temp_dir / ".knowledge"
    kb_dir.mkdir(exist_ok=True)

    # Create JSON files if provided
    if json_files:
        for filename, data in json_files.items():
            with open(kb_dir / filename, "w") as f:
                json.dump(data, f)

    # Create SQLite DB if learnings provided
    if learnings is not None:
        db_path = kb_dir / "knowledge.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE learnings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    source TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            for learning in learnings:
                conn.execute(
                    """INSERT INTO learnings
                       (id, title, category, content, metadata, source, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        learning.get("id", "unknown"),
                        learning.get("title", "Untitled"),
                        learning.get("category", "general"),
                        learning.get("content", ""),
                        json.dumps(learning.get("metadata", {})),
                        learning.get("source", "test"),
                        learning.get("created_at", "2024-01-01T00:00:00"),
                        learning.get("updated_at", "2024-01-01T00:00:00"),
                    ),
                )

    # Create AI.md if content provided
    if ai_md_content is not None:
        with open(kb_dir / "AI.md", "w") as f:
            f.write(ai_md_content)

    return str(kb_dir)


@pytest.mark.unit
def test_healthy_kb(temp_dir):
    """Test verification of a healthy KB with no issues."""
    learning = {
        "id": "learn-001",
        "title": "Test Learning",
        "category": "test",
        "content": "Test content",
        "source": "test",
    }

    # JSON file with matching DB entry
    json_files = {"learn-001.json": learning}

    # AI.md with matching content
    ai_md_content = "# AI Knowledge Base\n\n## Test\n\n### Test Learning\nTest content\n\n"

    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[learning],
        ai_md_content=ai_md_content,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "healthy"
    assert report.summary["error_count"] == 0
    assert report.summary["warning_count"] == 0
    assert report.summary["info_count"] > 0

    # Should have info findings about valid JSON, sync, etc.
    json_findings = [f for f in report.findings if f.category == "json"]
    assert any("valid and parseable" in f.message for f in json_findings)

    orphan_findings = [f for f in report.findings if f.category == "orphan"]
    # No orphaned entries should exist
    orphan_warnings = [f for f in orphan_findings if f.severity == "warning"]
    assert len(orphan_warnings) == 0


@pytest.mark.unit
def test_orphaned_json_file_detection(temp_dir):
    """Test detection of JSON files with no corresponding DB entry."""
    db_learning = {
        "id": "learn-db-only",
        "title": "DB Learning",
        "category": "general",
        "content": "Content",
        "source": "test",
    }

    # JSON file without a matching DB entry
    orphan_json = {
        "id": "learn-orphan-json",
        "title": "Orphan",
        "category": "general",
        "content": "Orphan content",
    }

    json_files = {
        "learn-db-only.json": db_learning,
        "learn-orphan-json.json": orphan_json,
    }

    ai_md_content = "# AI Knowledge Base\n\n## General\n\nSome content\n\n"

    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[db_learning],
        ai_md_content=ai_md_content,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "degraded"
    assert report.summary["warning_count"] > 0

    orphan_findings = [f for f in report.findings if f.category == "orphan"]
    orphan_warnings = [f for f in orphan_findings if f.severity == "warning"]
    assert len(orphan_warnings) >= 1

    # Check that the orphaned JSON is detected
    orphan_messages = " ".join(f.message for f in orphan_warnings)
    assert "Orphaned JSON file" in orphan_messages


@pytest.mark.unit
def test_orphaned_db_entry_detection(temp_dir):
    """Test detection of DB entries with no corresponding JSON file."""
    db_learning_1 = {
        "id": "learn-synced",
        "title": "Synced Learning",
        "category": "general",
        "content": "Content",
        "source": "test",
    }

    # DB entry without a matching JSON file
    db_learning_2 = {
        "id": "learn-orphan-db",
        "title": "Orphan DB",
        "category": "general",
        "content": "Content",
        "source": "test",
    }

    # Only one JSON file (synced)
    json_files = {"learn-synced.json": db_learning_1}

    ai_md_content = "# AI Knowledge Base\n\n## General\n\nSome content\n\n"

    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[db_learning_1, db_learning_2],
        ai_md_content=ai_md_content,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "degraded"
    assert report.summary["warning_count"] > 0

    orphan_findings = [f for f in report.findings if f.category == "orphan"]
    orphan_warnings = [f for f in orphan_findings if f.severity == "warning"]
    assert len(orphan_warnings) >= 1
    assert any("Orphaned DB entry" in f.message for f in orphan_warnings)


@pytest.mark.unit
def test_ai_md_inconsistency_detection(temp_dir):
    """Test detection of AI.md inconsistencies."""
    # DB has a "security" category but AI.md doesn't have it
    learning = {
        "id": "learn-001",
        "title": "Security Finding",
        "category": "security",
        "content": "Security content",
        "source": "test",
    }

    json_files = {"learn-001.json": learning}

    # AI.md missing the security category section
    ai_md_content = "# AI Knowledge Base\n\n## General\n\nSome content\n\n"

    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[learning],
        ai_md_content=ai_md_content,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "degraded"

    ai_md_findings = [f for f in report.findings if f.category == "ai_md"]
    ai_md_warnings = [f for f in ai_md_findings if f.severity == "warning"]
    assert len(ai_md_warnings) >= 1
    assert any(
        "missing sections" in f.message or "missing" in f.message.lower() for f in ai_md_warnings
    )


@pytest.mark.unit
def test_ai_md_missing_file(temp_dir):
    """Test detection of missing AI.md file."""
    learning = {
        "id": "learn-001",
        "title": "Some Learning",
        "category": "general",
        "content": "Content",
        "source": "test",
    }

    json_files = {"learn-001.json": learning}

    # No AI.md created
    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[learning],
        ai_md_content=None,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "degraded"
    ai_md_findings = [f for f in report.findings if f.category == "ai_md"]
    assert any("does not exist" in f.message for f in ai_md_findings)


@pytest.mark.unit
def test_empty_kb_handling(temp_dir):
    """Test verification of an empty KB directory."""
    kb_dir = temp_dir / ".knowledge"
    kb_dir.mkdir(exist_ok=True)

    verifier = KnowledgeBaseVerifier(knowledge_dir=str(kb_dir))
    report = verifier.verify()

    # No DB, no JSON, no AI.md → should be degraded (warnings) or critical
    assert report.status in ("degraded", "critical")

    # Should have findings about missing/no files
    assert len(report.findings) > 0


@pytest.mark.unit
def test_invalid_json_file_detection(temp_dir):
    """Test detection of invalid JSON files."""
    kb_dir = temp_dir / ".knowledge"
    kb_dir.mkdir(exist_ok=True)

    # Write an invalid JSON file
    with open(kb_dir / "broken.json", "w") as f:
        f.write("{ this is not valid json: ")

    verifier = KnowledgeBaseVerifier(knowledge_dir=str(kb_dir))
    report = verifier.verify()

    assert report.status == "critical"
    assert report.summary["error_count"] > 0

    json_findings = [f for f in report.findings if f.category == "json"]
    assert any("Invalid JSON" in f.message for f in json_findings)


@pytest.mark.unit
def test_empty_ai_md_file(temp_dir):
    """Test detection of empty AI.md file."""
    learning = {
        "id": "learn-001",
        "title": "Some Learning",
        "category": "general",
        "content": "Content",
        "source": "test",
    }

    json_files = {"learn-001.json": learning}
    ai_md_content = ""

    kb_dir = _create_test_kb(
        temp_dir,
        learnings=[learning],
        ai_md_content=ai_md_content,
        json_files=json_files,
    )

    verifier = KnowledgeBaseVerifier(knowledge_dir=kb_dir)
    report = verifier.verify()

    assert report.status == "degraded"
    ai_md_findings = [f for f in report.findings if f.category == "ai_md"]
    assert any("empty" in f.message.lower() or "size" in f.message.lower() for f in ai_md_findings)


@pytest.mark.unit
def test_missing_db_table(temp_dir):
    """Test detection of DB file without learnings table."""
    kb_dir = temp_dir / ".knowledge"
    kb_dir.mkdir(exist_ok=True)

    # Create a DB with no learnings table
    db_path = kb_dir / "knowledge.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE other_table (id TEXT)")

    ai_md_content = "# AI Knowledge Base\n\n"

    verifier = KnowledgeBaseVerifier(knowledge_dir=str(kb_dir))
    report = verifier.verify()

    assert report.status == "critical"
    db_findings = [f for f in report.findings if f.category == "db"]
    assert any(
        "learnings" in f.message.lower() and "missing" in f.message.lower() for f in db_findings
    )


@pytest.mark.unit
def test_non_existent_knowledge_dir():
    """Test verification of a non-existent knowledge directory."""
    verifier = KnowledgeBaseVerifier(knowledge_dir="/nonexistent/path/that/does/not/exist")
    report = verifier.verify()

    assert report.status == "critical"
    assert report.summary["error_count"] > 0


@pytest.mark.unit
def test_format_report():
    """Test report formatting."""
    findings = [
        VerificationFinding(severity="error", category="json", message="Bad JSON"),
        VerificationFinding(severity="warning", category="orphan", message="Orphaned file"),
        VerificationFinding(
            severity="info", category="db", message="All good", details="some detail"
        ),
    ]
    report = VerificationReport(status="degraded", findings=findings)
    formatted = format_report(report)

    assert "KB Verification Report" in formatted
    assert "DEGRADED" in formatted
    assert "❌" in formatted
    assert "⚠️" in formatted
    assert "ℹ️" in formatted
    assert "some detail" in formatted


@pytest.mark.unit
def test_report_determines_status_correctly():
    """Test that status determination works for all cases."""
    # No findings → healthy
    report1 = VerificationReport(status="healthy", findings=[])
    verifier = KnowledgeBaseVerifier(knowledge_dir="/some/path")
    assert verifier._determine_status([]) == "healthy"

    # Warnings only → degraded
    warnings = [VerificationFinding(severity="warning", category="orphan", message="orphan")]
    assert verifier._determine_status(warnings) == "degraded"

    # Has error → critical
    errors = [VerificationFinding(severity="error", category="json", message="bad")]
    assert verifier._determine_status(errors) == "critical"

    mixed = [
        VerificationFinding(severity="warning", category="orphan", message="orphan"),
        VerificationFinding(severity="error", category="json", message="bad"),
    ]
    assert verifier._determine_status(mixed) == "critical"
