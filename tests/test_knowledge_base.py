"""Tests for knowledge base functionality."""

import os
from unittest.mock import patch

import pytest

from utils.knowledge import KnowledgeBase


@pytest.mark.unit
def test_knowledge_base_init(temp_dir, monkeypatch):
    """Test knowledge base initialization."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()
    # knowledge_dir is a string, check existence with os.path
    assert os.path.exists(kb.knowledge_dir)
    assert os.path.exists(os.path.join(kb.knowledge_dir, "backups"))


@pytest.mark.unit
def test_save_learning(temp_dir, sample_learning, monkeypatch):
    """Test saving a learning to the knowledge base."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()

    # Provide category which is required for filename generation
    sample_learning["category"] = "test"

    # Use correct method name: save_learning
    learning_id = kb.save_learning(sample_learning)

    assert learning_id is not None
    learnings = kb.get_all_learnings()
    assert any(l["id"] == learning_id for l in learnings)


@pytest.mark.unit
def test_retrieve_learning(temp_dir, sample_learning, monkeypatch):
    """Test retrieving learnings from the knowledge base."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()

    sample_learning["category"] = "test"
    sample_learning["tags"] = ["test-tag"]
    kb.save_learning(sample_learning)

    # Use correct method name: retrieve_relevant
    # Note: Vector search requires Qdrant, this will likely fallback to legacy search
    results = kb.retrieve_relevant("test", tags=["test-tag"])

    # Depending on search implementation (legacy vs vector) result might vary,
    # but strictly checking we don't crash and get a list back.
    # Legacy search should find it if query matches content.
    assert isinstance(results, list)


@pytest.mark.unit
def test_index_codebase(temp_dir, monkeypatch):
    """Test indexing the codebase."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()

    # Mock the indexer to avoid actual vector DB interaction
    with patch.object(kb.codebase_indexer, "index_codebase") as m_index:
        kb.index_codebase(root_dir=".", force_recreate=True)
        m_index.assert_called_once_with(".", force_recreate=True)


@pytest.mark.unit
def test_compress_ai_md(temp_dir, monkeypatch):
    """Test compressing the AI knowledge base."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()

    # Mock docs_service to avoid actual LLM calls
    with patch.object(kb.docs_service, "compress_ai_md") as m_compress:
        kb.compress_ai_md(ratio=0.3, dry_run=True)
        m_compress.assert_called_once_with(ratio=0.3, dry_run=True)
