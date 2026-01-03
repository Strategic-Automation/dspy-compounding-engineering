from unittest.mock import MagicMock, patch

import dspy
from loguru import logger as loguru_logger

from utils.io.logger import logger
from utils.knowledge.core import KnowledgeBase
from utils.knowledge.extractor import codify_learning
from utils.web.documentation import DocumentationFetcher


def test_logger_depth_attribution():
    """
    Verify that our SystemLogger correctly attributes the log to the caller
    (depth=2) rather than the internal helper.
    """
    received_records = []

    def sink(message):
        received_records.append(message.record)

    # Add a temporary sink to capture records
    handler_id = loguru_logger.add(sink, format="{message}")
    try:
        # Call from this file
        logger.info("Verifying depth")

        assert len(received_records) > 0
        record = received_records[0]

        # The 'name' should contain 'test_hardening_verified'
        assert "test_hardening_verified" in record["name"]
        assert record["function"] == "test_logger_depth_attribution"
        assert "Verifying depth" in record["message"]
    finally:
        loguru_logger.remove(handler_id)


def test_ssrf_distinction():
    """
    Verify that DNS failures are warnings and specific,
    while SSRF blocks are errors.
    """
    fetcher = DocumentationFetcher()

    # 1. Test Blocked (localhost)
    with patch("utils.io.logger.loguru_logger.opt") as mock_opt:
        mock_logger = MagicMock()
        mock_opt.return_value = mock_logger

        res = fetcher.fetch("http://localhost")
        assert "Hostname 'localhost' is not permitted" in res
        # Should call error for SSRF
        expected_msg = (
            "SSRF Protection: Blocked potentially unsafe URL: "
            "http://localhost (Hostname 'localhost' is not permitted)"
        )
        mock_logger.log.assert_any_call("ERROR", expected_msg)

    # 2. Test DNS Failure (invalid domain)
    # Mocking resolve_ips to return empty list
    with patch("utils.web.documentation.DocumentationFetcher._resolve_ips", return_value=[]):
        with patch("utils.io.logger.loguru_logger.opt") as mock_opt:
            mock_logger = MagicMock()
            mock_opt.return_value = mock_logger

            res = fetcher.fetch("http://invalid-domain-123.com")
            assert "DNS resolution failed" in res
            # Should call warning for DNS failure
            expected_msg = (
                "Could not fetch http://invalid-domain-123.com: "
                "DNS resolution failed for invalid-domain-123.com"
            )
            mock_logger.log.assert_any_call("WARNING", expected_msg)


def test_kb_lock_paths():
    """Verify KB lock methods work as expected."""
    kb = KnowledgeBase()
    lock_path = kb.get_codify_lock_path()
    assert lock_path.endswith("codify.lock")

    lock = kb.get_lock("codify")
    assert lock.lock_file == lock_path


@patch("agents.workflow.feedback_codifier.FeedbackCodifier")
@patch("utils.knowledge.core.KnowledgeBase.save_learning")
def test_codify_learning_lm_guard(mock_save, mock_codifier):
    """Verify that codify_learning auto-configures dspy if LM is missing."""
    # Temporarily clear LM
    original_lm = dspy.settings.lm
    dspy.settings.configure(lm=None)

    try:
        # Mock result to skip actual LLM call but trigger the guard
        mock_codifier.return_value = MagicMock(codified_output=MagicMock())

        # We don't want to actually run the whole config as it might need keys,
        # but we want to verify the guard calls configure_dspy.
        with patch("config.configure_dspy") as mock_conf:
            codify_learning("test context", "test", "test", silent=True)
            mock_conf.assert_called_once()
    finally:
        # Restore LM
        dspy.settings.configure(lm=original_lm)
