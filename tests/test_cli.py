"""Tests for the CLI layer."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli import app

runner = CliRunner()


@pytest.fixture
def mock_workflows():
    """Mock all workflow functions to prevent actual execution."""
    with (
        patch("cli.run_triage") as m_triage,
        patch("cli.run_plan") as m_plan,
        patch("cli.run_unified_work") as m_work,
        patch("cli.run_review") as m_review,
        patch("cli.run_generate_command") as m_gen,
        patch("cli.run_codify") as m_codify,
    ):
        yield {
            "triage": m_triage,
            "plan": m_plan,
            "work": m_work,
            "review": m_review,
            "generate_command": m_gen,
            "codify": m_codify,
        }


@pytest.fixture
def mock_knowledge_base_class():
    """Mock KnowledgeBase class."""
    with patch("cli.KnowledgeBase") as m_kb:
        mock_instance = m_kb.return_value
        yield mock_instance


def test_triage_command(mock_workflows):
    result = runner.invoke(app, ["triage"])
    assert result.exit_code == 0
    mock_workflows["triage"].assert_called_once()


def test_plan_command(mock_workflows):
    result = runner.invoke(app, ["plan", "test feature"])
    assert result.exit_code == 0
    mock_workflows["plan"].assert_called_once_with("test feature")


def test_work_command(mock_workflows):
    result = runner.invoke(app, ["work", "001", "--dry-run", "--sequential"])
    assert result.exit_code == 0
    mock_workflows["work"].assert_called_once_with(
        pattern="001", dry_run=True, parallel=False, max_workers=3, in_place=True
    )


def test_review_command(mock_workflows):
    result = runner.invoke(app, ["review", "123", "--project"])
    assert result.exit_code == 0
    mock_workflows["review"].assert_called_once_with("123", project=True)


def test_generate_command(mock_workflows):
    result = runner.invoke(app, ["generate-command", "new feature"])
    assert result.exit_code == 0
    mock_workflows["generate_command"].assert_called_once_with(
        description="new feature", dry_run=False
    )


def test_codify_command(mock_workflows):
    result = runner.invoke(app, ["codify", "lesson learned", "--source", "retro"])
    assert result.exit_code == 0
    mock_workflows["codify"].assert_called_once_with(feedback="lesson learned", source="retro")


def test_compress_kb_command(mock_knowledge_base_class):
    result = runner.invoke(app, ["compress-kb", "--ratio", "0.3", "--dry-run"])
    assert result.exit_code == 0
    mock_knowledge_base_class.compress_ai_md.assert_called_once_with(ratio=0.3, dry_run=True)


def test_index_command(mock_knowledge_base_class):
    import os

    result = runner.invoke(app, ["index", "--dir", "src", "--force-recreate"])
    assert result.exit_code == 0
    mock_knowledge_base_class.index_codebase.assert_called_once_with(
        root_dir=os.path.abspath("src"), force_recreate=True
    )


def test_status_command():
    with patch("cli.get_system_status", return_value="System OK") as m_status:
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "System Diagnostics" in result.stdout
        assert "System OK" in result.stdout
        m_status.assert_called_once()
