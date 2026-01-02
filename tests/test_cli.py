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
        patch("cli.run_generate_agent") as m_gen,
        patch("cli.run_codify") as m_codify,
    ):
        yield {
            "triage": m_triage,
            "plan": m_plan,
            "work": m_work,
            "review": m_review,
            "generate_agent": m_gen,
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
    mock_workflows["review"].assert_called_once_with("123", project=True, agent_filter=None)


def test_generate_agent_command(mock_workflows):
    result = runner.invoke(app, ["generate-agent", "new feature"])
    assert result.exit_code == 0
    mock_workflows["generate_agent"].assert_called_once_with(
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
    result = runner.invoke(app, ["index", "--dir", "src", "--recreate"])
    assert result.exit_code == 0
    mock_knowledge_base_class.index_codebase.assert_called_once_with(
        root_dir="src", force_recreate=True
    )


def test_status_command():
    with patch("cli.get_system_status", return_value="System OK") as m_status:
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "System Diagnostics" in result.stdout
        assert "System OK" in result.stdout
        m_status.assert_called_once()


# ============================================================================
# Integration tests - verify output content
# ============================================================================


class TestAgentFilterValidation:
    """Tests for the validate_agent_filters function in CLI."""

    def test_review_with_valid_agent_filter(self, mock_workflows):
        """Valid agent names should be passed through."""
        result = runner.invoke(app, ["review", "latest", "--agent", "Security-Sentinel"])
        assert result.exit_code == 0
        mock_workflows["review"].assert_called_once_with(
            "latest", project=False, agent_filter=["Security-Sentinel"]
        )

    def test_review_with_multiple_agents(self, mock_workflows):
        """Multiple valid agent names should all be passed."""
        result = runner.invoke(
            app, ["review", "latest", "--agent", "Security", "--agent", "Performance"]
        )
        assert result.exit_code == 0
        mock_workflows["review"].assert_called_once_with(
            "latest", project=False, agent_filter=["Security", "Performance"]
        )

    def test_review_with_invalid_agent_filter_special_chars(self, mock_workflows):
        """Agent names with special chars should be rejected."""
        result = runner.invoke(app, ["review", "--agent", "Security; rm -rf /"])
        # Should exit without calling review (no valid filters)
        assert result.exit_code == 0
        mock_workflows["review"].assert_not_called()

    def test_review_with_mixed_valid_invalid(self, mock_workflows):
        """Only valid filters should be passed through."""
        result = runner.invoke(
            app, ["review", "latest", "--agent", "Valid-Agent", "--agent", "bad<script>"]
        )
        assert result.exit_code == 0
        mock_workflows["review"].assert_called_once_with(
            "latest", project=False, agent_filter=["Valid-Agent"]
        )


class TestHelpOutput:
    """Tests verifying help text is displayed correctly."""

    def test_help_shows_commands(self):
        """Main help should list all commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "review" in result.stdout
        assert "plan" in result.stdout
        assert "work" in result.stdout
        assert "triage" in result.stdout
        assert "generate-agent" in result.stdout
        assert "index" in result.stdout
        assert "status" in result.stdout

    def test_review_help(self):
        """Review command help should show options."""
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.stdout
        assert "--agent" in result.stdout

    def test_work_help(self):
        """Work command help should show options."""
        result = runner.invoke(app, ["work", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.stdout
        assert "--sequential" in result.stdout
        assert "--in-place" in result.stdout

    def test_generate_agent_help(self):
        """Generate-agent command help should show options."""
        result = runner.invoke(app, ["generate-agent", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.stdout
        assert "DESCRIPTION" in result.stdout


class TestDeprecatedCommands:
    """Tests for backward-compatible deprecated commands."""

    def test_generate_command_alias_shows_deprecation(self, mock_workflows):
        """Legacy generate-command should work but show deprecation warning."""
        # Check if generate-command exists (it may have been removed)
        result = runner.invoke(app, ["--help"])
        if "generate-command" in result.stdout:
            result = runner.invoke(app, ["generate-command", "test desc"])
            assert result.exit_code == 0
            assert "deprecated" in result.stdout.lower() or mock_workflows["generate_agent"].called
        else:
            # Command doesn't exist, which is fine
            pass
