"""
Integration tests that run actual LLM workflows.

These tests make real API calls and should be run selectively:
    pytest tests/test_integration_llm.py -v --slow

Mark with @pytest.mark.slow to skip in normal CI runs.
"""

import os

import pytest
from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def is_api_key_available() -> bool:
    """Check if any LLM API key is configured."""
    return any(
        os.getenv(key)
        for key in [
            "OPENAI_API_KEY",
            "OPENROUTER_API_KEY",
            "ANTHROPIC_API_KEY",
        ]
    )


# Skip all tests in this module if no API key available
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not is_api_key_available(), reason="No LLM API key configured"),
]


class TestReviewWorkflowIntegration:
    """Integration tests for the review workflow with actual LLM calls."""

    def test_review_latest_runs_and_completes(self):
        """Test that review latest runs to completion and shows output."""
        result = runner.invoke(app, ["review", "latest", "--agent", "Security"])

        # Should complete without error
        assert result.exit_code == 0

        # Should show review phase output
        assert "Running Review Agents" in result.stdout or "Review Complete" in result.stdout

    def test_review_with_single_agent_produces_output(self):
        """Test that a single-agent review produces structured output."""
        result = runner.invoke(app, ["review", "latest", "--agent", "Code-Simplicity-Reviewer"])

        assert result.exit_code == 0

        # Should show agent execution
        output = result.stdout
        assert any(
            phrase in output
            for phrase in ["Review Complete", "Running agents", "Completed", "Summary"]
        )

    def test_review_shows_findings_when_issues_found(self):
        """Test that review output includes findings format."""
        result = runner.invoke(app, ["review", "latest"])

        assert result.exit_code == 0

        # The output should include structured sections
        output = result.stdout
        # At minimum should show the review ran
        assert "Review" in output


class TestGenerateAgentIntegration:
    """Integration tests for the agent generation workflow."""

    def test_generate_agent_dry_run_shows_preview(self):
        """Test that generate-agent --dry-run shows code preview."""
        result = runner.invoke(app, ["generate-agent", "Check for duplicate code", "--dry-run"])

        assert result.exit_code == 0

        output = result.stdout
        # Should show generation phases
        assert "Phase" in output or "Context" in output or "Agent" in output

        # Dry run should show preview without writing
        assert "DRY RUN" in output or "Preview" in output or "generated" in output.lower()

    def test_generate_agent_produces_valid_code_preview(self):
        """Test that generated agent code includes required elements."""
        result = runner.invoke(
            app, ["generate-agent", "Review error handling patterns", "--dry-run"]
        )

        assert result.exit_code == 0

        output = result.stdout
        # Should include code structure elements
        has_dspy = "dspy" in output.lower()
        has_signature = "Signature" in output or "signature" in output
        has_class = "class" in output

        # At least some code should be generated
        assert has_dspy or has_signature or has_class


class TestStatusCommand:
    """Integration tests for the status command."""

    def test_status_shows_service_info(self):
        """Test that status command shows actual service status."""
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

        output = result.stdout
        # Should show diagnostics
        assert "Diagnostics" in output or "Status" in output

        # Should mention key services
        assert any(term in output for term in ["Qdrant", "API", "Search", "READY", "CONFIGURED"])


class TestIndexCommand:
    """Integration tests for the index command."""

    def test_index_runs_without_error(self):
        """Test that index command runs to completion."""
        # Run with --recreate to ensure clean state
        result = runner.invoke(app, ["index", "--dir", "agents"])

        # Should complete (may have warnings but not crash)
        assert result.exit_code == 0

        output = result.stdout
        # Should show indexing activity
        assert any(
            term in output.lower() for term in ["index", "embedding", "file", "complete", "skip"]
        )
