from unittest.mock import MagicMock, patch

import pytest

from utils.web.documentation import DocumentationFetcher


@pytest.fixture
def fetcher():
    return DocumentationFetcher(use_jina=False)


@patch("httpx.Client.get")
def test_fetch_locally_success(mock_get, fetcher):
    # Mock successful HTML response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        "<html><body><header>Nav</header><main><h1>Title</h1><p>Content</p></main></body></html>"
    )
    mock_get.return_value = mock_response

    result = fetcher.fetch("https://example.com/docs")

    # Check that it converted to markdown and removed header
    assert "# Title" in result
    assert "Content" in result
    assert "Nav" not in result


@patch("httpx.Client.get")
def test_fetch_locally_failure(mock_get, fetcher):
    # Mock failed response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = Exception("Not Found")
    mock_get.return_value = mock_response

    result = fetcher.fetch("https://example.com/docs")
    assert "Error: Unable to fetch documentation" in result
    assert "Not Found" in result


@patch("utils.web.documentation.DocumentationFetcher._fetch_via_jina")
def test_fetch_via_jina_success(mock_jina):
    fetcher = DocumentationFetcher(use_jina=True)
    mock_jina.return_value = "# Jina Content"

    result = fetcher.fetch("https://example.com/docs")
    assert result == "# Jina Content"
    mock_jina.assert_called_once()
