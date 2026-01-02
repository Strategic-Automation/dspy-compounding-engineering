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


def format_search_results(results: list[dict]) -> str:
    """Format structured search results into a markdown string for LLM consumption."""
    if not results or (len(results) == 1 and results[0].get("title") == "Search Error"):
        # Handle errors or empty results
        if results and results[0].get("title") == "Search Error":
            return f"Search failed: {results[0].get('source')}"
        return "No search results found."

    output = []
    for r in results:
        title = r.get("title", "No Title")
        url = r.get("url", "No URL")
        source = r.get("source", "Unknown")
        output.append(f"- **{title}**\n  URL: {url}\n  Source: {source}")

    return "\n\n".join(output)


def internet_search(query: str, max_results: int = 5) -> str:
    """
    Consolidated function for searching the internet and returning formatted markdown.
    This is the primary entry point for agent tools.
    """
    results = search_web(query, max_results=max_results)
    return format_search_results(results)
