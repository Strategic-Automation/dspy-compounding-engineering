import os
from unittest.mock import patch, MagicMock
from config import ServiceRegistry

def test_registry_singleton():
    reg1 = ServiceRegistry()
    reg2 = ServiceRegistry()
    assert reg1 is reg2

def test_registry_initial_status():
    reg = ServiceRegistry()
    status = reg.status
    assert "qdrant_available" in status
    assert "openai_key_available" in status
    assert "learnings_ensured" in status

@patch("qdrant_client.QdrantClient")
def test_registry_check_qdrant_caching(mock_qdrant_class):
    # Reset status for test
    reg = ServiceRegistry()
    reg.status["qdrant_available"] = None
    
    mock_client = MagicMock()
    mock_qdrant_class.return_value = mock_client
    
    # First call
    result1 = reg.check_qdrant()
    assert result1 is True
    assert mock_qdrant_class.call_count == 1
    
    # Second call (should be cached)
    result2 = reg.check_qdrant()
    assert result2 is True
    assert mock_qdrant_class.call_count == 1

def test_registry_check_api_keys_logic():
    reg = ServiceRegistry()
    reg.status["openai_key_available"] = None
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "DSPY_LM_PROVIDER": "openai"}):
        assert reg.check_api_keys(force=True) is True
        
    reg.status["openai_key_available"] = None
    with patch.dict(os.environ, {"DSPY_LM_PROVIDER": "openai"}, clear=True):
        # No key in env
        assert reg.check_api_keys(force=True) is False
