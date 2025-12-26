from unittest.mock import MagicMock

import pytest

from utils.knowledge.indexer import CodebaseIndexer


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def mock_embedding_provider():
    m = MagicMock()
    m.vector_size = 1536
    m.get_embedding.return_value = [0.1] * 1536
    return m


@pytest.fixture
def indexer(mock_client, mock_embedding_provider, monkeypatch):
    # Avoid _ensure_collection during init for pure unit tests
    monkeypatch.setattr(CodebaseIndexer, "_ensure_collection", lambda *args, **kwargs: None)
    return CodebaseIndexer(mock_client, mock_embedding_provider)


def test_chunk_text_basic(indexer):
    text = "A" * 5000
    chunks = indexer._chunk_text(text, size=2000, overlap=200)

    # 1. 0:2000
    # 2. 1800:3800
    # 3. 3600:5000 (shorter)
    assert len(chunks) == 3
    assert len(chunks[0]) == 2000
    assert len(chunks[1]) == 2000
    assert len(chunks[2]) == 1400


def test_chunk_text_small(indexer):
    text = "Short text"
    chunks = indexer._chunk_text(text, size=2000, overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty(indexer):
    assert indexer._chunk_text("") == []
    assert indexer._chunk_text(None) == []


def test_index_single_file_skipped_matching_mtime(indexer):
    filepath = "test.py"
    full_path = "full/test.py"
    indexed_files = {filepath: 1000.0}

    from unittest.mock import patch

    with patch("os.path.getmtime", return_value=1000.0):
        assert indexer._index_single_file(filepath, full_path, indexed_files) is False


def test_index_single_file_unicode_error_skips(indexer):
    filepath = "binary.bin"
    full_path = "full/binary.bin"
    indexed_files = {}

    from unittest.mock import patch

    with (
        patch("os.path.getmtime", return_value=1234.0),
        patch("builtins.open", MagicMock()) as mock_open,
    ):
        mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, ""
        )
        assert indexer._index_single_file(filepath, full_path, indexed_files) is False
