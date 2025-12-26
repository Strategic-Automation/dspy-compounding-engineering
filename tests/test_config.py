import os
from pathlib import Path
from unittest.mock import patch

import pytest

from config import load_configuration


@pytest.fixture
def temp_env_files(tmp_path):
    """Create temporary .env files for testing."""
    local_env = tmp_path / ".env"
    local_env.write_text("TEST_VAR=local\nOPENAI_API_KEY=local_key")

    global_dir = tmp_path / ".config" / "compounding"
    global_dir.mkdir(parents=True)
    global_env = global_dir / ".env"
    global_env.write_text("TEST_VAR=global\nGLOBAL_ONLY=true")

    return {"local": local_env, "global": global_env, "global_dir": global_dir}


def test_load_configuration_priority(temp_env_files, monkeypatch):
    """Test that configuration priority is respected."""
    # Mocking os.path.expanduser to point to our temp global dir
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda x: str(temp_env_files["global_dir"].parent.parent)
        if "config" in x
        else str(temp_env_files["global_dir"].parent.parent),
    )

    # We need to be careful with how load_dotenv is called in config.py
    # Since we use os.getcwd() and expanduser, we should mock those or change CWD

    monkeypatch.chdir(temp_env_files["local"].parent)

    # Mock os.path.exists to return True for our specific paths
    original_exists = os.path.exists

    def mock_exists(path):
        if ".config/compounding/.env" in str(path):
            return True
        if str(path).endswith(".env") and temp_env_files["local"].parent == Path(path).parent:
            return True
        return original_exists(path)

    with patch("os.path.exists", side_effect=mock_exists):
        with patch("config.load_dotenv") as mock_load:
            load_configuration()

            # Should be called (local and global)
            assert mock_load.call_count >= 1

            # Check that local .env was loaded override=True
            # We search through all calls to find the one for the local .env
            local_call = None
            for call in mock_load.call_args_list:
                args, kwargs = call
                path = kwargs.get("dotenv_path") or (args[0] if args else None)
                if path and str(path).endswith(".env") and ".config" not in str(path):
                    local_call = call
                    break

            assert local_call is not None
            assert local_call.kwargs.get("override") is True


def test_load_configuration_explicit(tmp_path):
    """Test that explicit env file takes precedence."""
    explicit_env = tmp_path / "explicit.env"
    explicit_env.write_text("TEST_VAR=explicit")

    with patch("os.path.exists", return_value=True):
        with patch("config.load_dotenv") as mock_load:
            load_configuration(env_file=str(explicit_env))

            # Find the call for the explicit file
            explicit_call = None
            for call in mock_load.call_args_list:
                args, kwargs = call
                path = kwargs.get("dotenv_path") or (args[0] if args else None)
                if str(path) == str(explicit_env):
                    explicit_call = call
                    break

            assert explicit_call is not None
            assert explicit_call.kwargs.get("override") is True
