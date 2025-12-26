import os
from unittest.mock import MagicMock, patch

import pytest

# Inject mocks before ANY internal imports
from utils.context.project import ProjectContext
from utils.context.scrubber import scrubber

# from .mock_modules import patch_all ... already happens on import
from utils.knowledge.core import KnowledgeBase
from utils.knowledge.indexer import CodebaseIndexer


@pytest.fixture
def mock_qdrant():
    with patch("utils.knowledge.core.QdrantClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


def test_project_hash_length():
    from config import get_project_hash

    h = get_project_hash()
    assert len(h) == 16


def test_dimension_mismatch_kb_is_safe(mock_qdrant):
    # Scenario: Mismatch exists
    mock_qdrant.collection_exists.return_value = True
    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors.size = 1536
    mock_qdrant.get_collection.return_value = mock_collection_info

    # Mocking EmbeddingProvider to return size 512
    with patch("utils.knowledge.core.EmbeddingProvider") as mock_ep_cls:
        mock_ep = MagicMock()
        mock_ep.vector_size = 512
        mock_ep_cls.return_value = mock_ep

        kb = KnowledgeBase()
        # Should NOT call delete_collection
        mock_qdrant.delete_collection.assert_not_called()
        assert kb.vector_db_available is False


def test_dimension_mismatch_indexer_is_safe(mock_qdrant):
    mock_qdrant.collection_exists.return_value = True
    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors.size = 1536
    mock_qdrant.get_collection.return_value = mock_collection_info

    mock_ep = MagicMock()
    mock_ep.vector_size = 512

    indexer = CodebaseIndexer(mock_qdrant, mock_ep)
    # Should NOT call delete_collection
    mock_qdrant.delete_collection.assert_not_called()
    assert indexer.vector_db_available is False


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
            mock_qdrant.delete.assert_called_once()
            args, kwargs = mock_qdrant.delete.call_args
            # Verify the range filter for chunk_index >= 1
            assert "points_selector" in kwargs
            # We can't easily inspect the filter object deeply without knowing its
            # internal structure perfectly, but we can check it was called.
            assert kwargs["collection_name"] == indexer.collection_name


def test_pii_scrubbing():
    text = "My key is sk-12345678901234567890123456789012 and email is test@example.com"
    scrubbed = scrubber.scrub(text)
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
