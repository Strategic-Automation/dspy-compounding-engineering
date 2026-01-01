"""DuckDuckGo search implementation for research agents."""

from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of search results, each containing:
        - title: Page title
        - url: Page URL
        - source: Data source identifier (always 'DuckDuckGo')

    Example:
        >>> results = search_web("python best practices 2024")
        >>> for result in results:
        ...     print(result['title'], result['url'])
    """
    try:
        # DDGS().text() returns generator, we limit and convert to list
        ddgs = DDGS(timeout=10)
        raw_results = ddgs.text(query, max_results=max_results)

        # Convert to our standard format
        results = []
        for item in raw_results:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "source": "DuckDuckGo",
                }
            )

        return results

    except Exception as e:
        # Return error info in structured format
        return [{"title": "Search Error", "url": "", "source": f"Error: {str(e)}"}]
