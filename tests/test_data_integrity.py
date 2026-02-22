import os
from unittest.mock import MagicMock, patch

import pytest

# Inject mocks before ANY internal imports
from utils.context.project import ProjectContext

# from .mock_modules import patch_all ... already happens on import
from utils.knowledge.core import KnowledgeBase
from utils.knowledge.indexer import CodebaseIndexer
from utils.security.scrubber import SecretScrubber


@pytest.fixture
def mock_qdrant():
    # We don't need to patch the class if we pass the mock explicitly
    mock_client = MagicMock()
    # If isinstance checks are needed, we might need to mock the class in sys.modules or use spec
    return mock_client


def test_project_hash_length():
    from config import get_project_hash

    h = get_project_hash()
    assert len(h) == 16


def test_dimension_mismatch_kb_is_safe(mock_qdrant):
    # Scenario: Mismatch exists - Collection size 1536 vs Embedding size 512

    # Mock collection info response
    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors.size = 1536
    mock_qdrant.get_collection.return_value = mock_collection_info

    # Ensure collection_exists returns True so it checks dimension
    mock_qdrant.collection_exists.return_value = True

    # Mocking EmbeddingProvider to return size 512
    with patch("utils.knowledge.core.EmbeddingProvider") as mock_ep_cls:
        mock_ep = MagicMock()
        mock_ep.vector_size = 512
        mock_ep_cls.return_value = mock_ep

        kb = KnowledgeBase(qdrant_client=mock_qdrant)

        # Internal safe check should have caught mismatch and set flag to False
        assert kb.vector_db_available is False
        # And crucially, should NOT have deleted the collection
        mock_qdrant.delete_collection.assert_not_called()


def test_dimension_mismatch_indexer_is_safe(mock_qdrant):
    # Mock collection info
    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors.size = 1536
    mock_qdrant.get_collection.return_value = mock_collection_info
    mock_qdrant.collection_exists.return_value = True

    mock_ep = MagicMock()
    mock_ep.vector_size = 512

    indexer = CodebaseIndexer(mock_qdrant, mock_ep)

    # Should detect mismatch
    assert indexer.vector_db_available is False
    # Should NOT call delete_collection
    mock_qdrant.delete_collection.assert_not_called()


def test_indexer_shrinkage_cleanup(mock_qdrant):
    mock_ep = MagicMock()
    indexer = CodebaseIndexer(mock_qdrant, mock_ep)

    # Simulate indexing a file that has 3 chunks
    filepath = "test.py"
    with (
        patch("os.path.getmtime", return_value=1234.5),
        patch("builtins.open", MagicMock()) as mock_open,
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = "content"

    # Mocking _chunk_text to return 1 chunk (simulating shrinkage from a previous 2-chunk state)
        with patch.object(indexer, "_chunk_text", return_value=["chunk1"]):
            indexer._index_single_file(filepath, "full/path/test.py", {})

            # verify delete was called with chunk_index filter
            # There might be upsert calls too, so we check specifically for delete
            assert mock_qdrant.delete.called

            # Inspect the calls
            delete_calls = mock_qdrant.delete.call_args_list
            assert len(delete_calls) > 0

            # Check arguments of the last call or find the correct one
            _, kwargs = delete_calls[0]
            assert "points_selector" in kwargs
            assert kwargs["collection_name"] == indexer.collection_name


def test_pii_scrubbing():
    text = "My key is sk-12345678901234567890123456789012 and email is test@example.com"
    scrubbed = SecretScrubber().scrub(text)
    assert "sk-" not in scrubbed
    assert "test@example.com" not in scrubbed
    assert "[REDACTED_OPENAI_API_KEY]" in scrubbed
    assert "[REDACTED_EMAIL]" in scrubbed


def test_project_context_scrubbing(temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    os.makedirs("src")
    secret_file = "src/secrets.py"
    with open(secret_file, "w") as f:
        f.write("sk-12345678901234567890123456789012")

    ctx = ProjectContext(base_dir=".")
    content = ctx.gather_smart_context(task="review code")

    assert "sk-" not in content
    assert "[REDACTED_OPENAI_API_KEY]" in content
