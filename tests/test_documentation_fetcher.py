from unittest.mock import MagicMock, patch

import pytest

from utils.web.documentation import DocumentationFetcher


@pytest.fixture
def fetcher():
    return DocumentationFetcher(use_jina=False)


@patch("utils.web.documentation.DocumentationFetcher._get_playwright")
@patch("utils.web.documentation.DocumentationFetcher._get_safe_ip")
@patch("httpx.Client.get")
def test_fetch_locally_success(mock_get, mock_get_ip, mock_get_playwright, fetcher):
    # Mock playwright unavailable
    mock_get_playwright.return_value = None

    # Mock safe IP resolution
    mock_get_ip.return_value = ("1.2.3.4", None)

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


@patch("utils.web.documentation.DocumentationFetcher._get_playwright")
@patch("utils.web.documentation.DocumentationFetcher._get_safe_ip")
@patch("httpx.Client.get")
def test_fetch_locally_failure(mock_get, mock_get_ip, mock_get_playwright, fetcher):
    # Mock playwright unavailable
    mock_get_playwright.return_value = None

    # Mock safe IP resolution
    mock_get_ip.return_value = ("1.2.3.4", None)

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


@patch("utils.web.documentation.DocumentationFetcher._get_playwright")
@patch("utils.web.documentation.DocumentationFetcher._get_safe_ip")
@patch("utils.web.documentation.DocumentationFetcher._fetch_via_jina")
@patch("httpx.Client.get")
def test_jina_failure_fallback_to_local(mock_get, mock_jina, mock_get_ip, mock_get_playwright):
    # Create fetcher with jina enabled
    fetcher = DocumentationFetcher(use_jina=True)

    # Mock Jina failure
    mock_jina.side_effect = Exception("Jina service unavailable")

    # Mock playwright unavailable
    mock_get_playwright.return_value = None

    # Mock safe IP resolution for fallback
    mock_get_ip.return_value = ("1.2.3.4", None)

    # Mock successful local HTML response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><h1>Local Title</h1></body></html>"
    mock_get.return_value = mock_response

    # Should fall back to local parsing
    result = fetcher.fetch("https://example.com/docs")

    assert "# Local Title" in result
    mock_jina.assert_called_once()
    mock_get.assert_called_once()


@patch("utils.web.documentation.DocumentationFetcher._get_playwright")
def test_fetch_via_playwright_success(mock_get_playwright):
    # Setup mock playwright structure
    mock_playwright = MagicMock()
    mock_get_playwright.return_value = mock_playwright
    mock_p = mock_playwright.return_value.__enter__.return_value
    mock_browser = mock_p.chromium.launch.return_value
    mock_page = mock_browser.new_page.return_value
    mock_page.content.return_value = "<html><body><h1>Playwright Title</h1></body></html>"

    fetcher = DocumentationFetcher(use_jina=False)
    result = fetcher.fetch("https://example.com/docs")

    assert "# Playwright Title" in result
    mock_page.goto.assert_called_once()
    mock_browser.close.assert_called_once()
