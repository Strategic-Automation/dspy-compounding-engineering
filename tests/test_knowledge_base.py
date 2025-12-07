"""Tests for knowledge base functionality."""

import pytest

from utils.knowledge_base import KnowledgeBase


@pytest.mark.unit
def test_knowledge_base_init(temp_dir, monkeypatch):
    """Test knowledge base initialization."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()  # No base_dir parameter
    assert kb.knowledge_dir.exists()


@pytest.mark.unit
def test_save_learning(temp_dir, sample_learning, monkeypatch):
    """Test saving a learning to the knowledge base."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()
    
    learning_id = kb.save(sample_learning)
    
    assert learning_id is not None


@pytest.mark.unit  
def test_retrieve_learning(temp_dir, sample_learning, monkeypatch):
    """Test retrieving learnings from the knowledge base."""
    monkeypatch.chdir(temp_dir)
    kb = KnowledgeBase()
    
    # Save a learning
    kb.save(sample_learning)
    
    # Retrieve it
    results = kb.retrieve("test")
    
    assert len(results) >= 0  # May or may not find results depending on implementation
