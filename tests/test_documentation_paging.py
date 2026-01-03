from unittest.mock import patch

from utils.web.documentation import DocumentationFetcher


class TestDocumentationPaging:
    def test_truncate_to_limit_no_truncation(self):
        fetcher = DocumentationFetcher()
        content = "Hello world"
        truncated = fetcher._truncate_to_limit(content, max_tokens=10)
        assert truncated == content

    def test_truncate_to_limit_with_truncation(self):
        fetcher = DocumentationFetcher()
        content = "word " * 100
        max_tokens = 50
        truncated = fetcher._truncate_to_limit(content, max_tokens=max_tokens)

        # Check truncation markers
        assert "[TRUNCATED" in truncated
        assert len(truncated) < len(content)

    def test_truncate_to_limit_with_offset(self):
        fetcher = DocumentationFetcher()
        content = "FirstSegment SecondSegment ThirdSegment"

        # Get total tokens first to pick a good offset
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        enc.encode(content)  # Verify encoding works
        # "FirstSegment" is ~2 tokens

        # Test offset skips "FirstSegment" (which is the first ~2 tokens)
        # We'll skip 3 tokens to be sure we're in the second segment
        truncated = fetcher._truncate_to_limit(content, max_tokens=10, offset_tokens=3)
        assert "FirstSegment" not in truncated
        assert "SecondSegment" in truncated or "ThirdSegment" in truncated

    @patch("utils.web.documentation.DocumentationFetcher._fetch_via_jina")
    def test_fetch_with_paging_instructions(self, mock_jina):
        mock_jina.return_value = "Long content " * 100
        fetcher = DocumentationFetcher()

        # Fetch with small limit
        result = fetcher.fetch("https://example.com", max_tokens=10)

        assert "[TRUNCATED" in result
        assert "offset_tokens=10" in result
