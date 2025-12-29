from typing import Optional

import dspy
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from ..io.logger import logger


class DocumentationFetcher:
    """
    Utility for fetching and parsing official documentation from URLs.
    Supports high-quality conversion via r.jina.ai and local fallback.
    """

    def __init__(self, use_jina: bool = True, timeout: int = 10):
        self.use_jina = use_jina
        self.timeout = timeout

    def fetch(self, url: str) -> str:
        """
        Fetch documentation from a URL and return it as Markdown.
        """
        if not url.startswith("http"):
            return f"Invalid URL: {url}"

        if self.use_jina:
            try:
                content = self._fetch_via_jina(url)
                if content:
                    logger.success(f"Successfully fetched documentation via Jina for {url}")
                    return content
            except Exception as e:
                logger.warning(f"Jina fetch failed for {url}: {e}. Falling back to local parsing.")

        return self._fetch_locally(url)

    def _fetch_via_jina(self, url: str) -> Optional[str]:
        """
        Fetch via r.jina.ai for high-quality markdown.
        """
        jina_url = f"https://r.jina.ai/{url}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(jina_url)
            response.raise_for_status()
            return response.text

    def _fetch_locally(self, url: str) -> str:
        """
        Fallback fetch and parse locally using BeautifulSoup and markdownify.
        """
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove non-content elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()

                # Convert to markdown
                markdown_content = md(str(soup), heading_style="ATX")
                logger.success(f"Successfully fetched and parsed documentation locally for {url}")
                return markdown_content.strip()
        except Exception as e:
            logger.error(f"Local documentation fetch failed for {url}", detail=str(e))
            return (
                f"Error: Unable to fetch documentation from {url} locally: {e}. "
                "Please check the URL or try again later."
            )


def get_documentation_tool():
    """Returns the documentation tool for dspy agents."""
    fetcher = DocumentationFetcher()

    def fetch_documentation(url: str) -> str:
        """
        Fetches and parses official documentation from a given URL.
        Use this to get up-to-date API references, guides, and examples.
        """
        return fetcher.fetch(url)

    return dspy.Tool(fetch_documentation)
