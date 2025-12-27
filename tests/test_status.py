from unittest.mock import patch

from utils.io.status import get_system_status


def test_get_system_status_all_ready():
    with (
        patch("config.registry.check_qdrant", return_value=True),
        patch("config.registry.check_api_keys", return_value=True),
    ):
        status = get_system_status()
        assert "**Qdrant Vector DB**: READY" in status
        assert "**API Keys**: CONFIGURED" in status
        assert "Search Mode**: Semantic" in status


def test_get_system_status_qdrant_down():
    with (
        patch("config.registry.check_qdrant", return_value=False),
        patch("config.registry.check_api_keys", return_value=True),
    ):
        status = get_system_status()
        assert "UNAVAILABLE" in status
        assert "Keyword only" in status
        assert "**API Keys**: CONFIGURED" in status


def test_get_system_status_keys_missing():
    with (
        patch("config.registry.check_qdrant", return_value=True),
        patch("config.registry.check_api_keys", return_value=False),
    ):
        status = get_system_status()
        assert "**API Keys**: MISSING" in status


def test_get_system_status_error():
    with patch("config.registry.check_qdrant", side_effect=Exception("Registry error")):
        status = get_system_status()
        assert "Error retrieving system status: Registry error" in status
