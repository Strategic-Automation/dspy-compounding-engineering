import os
from unittest.mock import patch

from utils.io.logger import SystemLogger


def test_logger_info_output():
    with patch("utils.io.logger.console.log") as mock_log:
        with patch.dict(os.environ, {"COMPOUNDING_QUIET": "false"}):
            SystemLogger.info("Test Info", to_cli=True)
            mock_log.assert_called_once()
            args, _ = mock_log.call_args
            assert "Test Info" in args[0]


def test_logger_quiet_mode():
    with patch("utils.io.logger.console.print") as mock_print:
        # True as string
        with patch.dict(os.environ, {"COMPOUNDING_QUIET": "true"}):
            SystemLogger.info("Hidden Info")
            mock_print.assert_not_called()


def test_logger_error_always_shows():
    with patch("utils.io.logger.console.print") as mock_print:
        with patch.dict(os.environ, {"COMPOUNDING_QUIET": "true"}):
            SystemLogger.error("Critical Error")
            # Error should bypass quiet mode or at least show the red header
            assert mock_print.called
            args, _ = mock_print.call_args
            assert "ERROR:" in args[0]


def test_logger_warning_always_shows():
    with patch("utils.io.logger.console.print") as mock_print:
        with patch.dict(os.environ, {"COMPOUNDING_QUIET": "true"}):
            SystemLogger.warning("Be careful")
            mock_print.assert_called_once()
            args, _ = mock_print.call_args
            assert "WARNING:" in args[0]


def test_logger_success_quiet():
    with patch("utils.io.logger.console.print") as mock_print:
        with patch.dict(os.environ, {"COMPOUNDING_QUIET": "true"}):
            SystemLogger.success("Won't see this")
            mock_print.assert_not_called()
