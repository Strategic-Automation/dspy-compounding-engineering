from unittest.mock import MagicMock, patch

import pytest

from utils.knowledge.core import KnowledgeBase
from utils.knowledge.indexer import CodebaseIndexer


@pytest.fixture
def mock_qdrant_client():
    with patch("utils.knowledge.core.QdrantClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_embedding_provider():
    with patch("utils.knowledge.core.EmbeddingProvider") as mock_provider_cls:
        mock_provider = MagicMock()
        mock_provider.vector_size = 512  # Current configured size
        mock_provider_cls.return_value = mock_provider
        yield mock_provider


def test_knowledge_base_recreates_collection_on_mismatch(temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)

    # Mock dependencies
    with (
        patch("utils.knowledge.core.QdrantClient") as mock_client_cls,
        patch("utils.knowledge.core.EmbeddingProvider") as mock_provider_cls,
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_provider = MagicMock()
        mock_provider.vector_size = 512
        mock_provider_cls.return_value = mock_provider

        # Scenario: Collection exists but has size 1536
        mock_client.collection_exists.return_value = True

        # Mock get_collection response structure
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1536
        mock_collection_info.config.params.vectors.__class__ = object

        mock_client.get_collection.return_value = mock_collection_info

        # Initialize KnowledgeBase
        # Mismatch - should disable vector DB by default
        kb = KnowledgeBase()
        assert kb.vector_db_available is False
        mock_client.delete_collection.assert_not_called()

        # Now force recreate
        kb._ensure_collection(force_recreate=True)

        # Check logic
        # 1. get_collection called
        mock_client.get_collection.assert_called_with(kb.collection_name)
        # 2. delete_collection called
        mock_client.delete_collection.assert_called_with(kb.collection_name)
        # 3. create_collection called with new size
        mock_client.create_collection.assert_called()
        call_args = mock_client.create_collection.call_args
        assert call_args.kwargs["vectors_config"].size == 512


def test_codebase_indexer_recreates_collection_on_mismatch(temp_dir, monkeypatch):
    # Mock CodebaseChecker's ensure_collection
    mock_client = MagicMock()
    mock_provider = MagicMock()
    mock_provider.vector_size = 512

    # Scenario: Collection exists with mismatch
    mock_client.collection_exists.return_value = True

    # Mock mismatching vector config
    mock_collection_info = MagicMock()
    # Mocking as if it returns an object with .size
    mock_collection_info.config.params.vectors.size = 1536
    mock_client.get_collection.return_value = mock_collection_info

    # Scenario: Mismatch exists - should disable
    indexer = CodebaseIndexer(mock_client, mock_provider)
    assert indexer.vector_db_available is False
    mock_client.delete_collection.assert_not_called()

    # Now force
    indexer.index_codebase(force_recreate=True)

    # Assertions
    mock_client.get_collection.assert_called_with(indexer.collection_name)
    mock_client.delete_collection.assert_called_with(indexer.collection_name)
    mock_client.create_collection.assert_called()
    assert mock_client.create_collection.call_args.kwargs["vectors_config"].size == 512
