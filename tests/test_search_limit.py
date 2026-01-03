from utils.io.files import search_files


def test_search_files_limit():
    # Search for "import" in the "agents" directory with a low limit
    # We know "import" appears many times
    results = search_files(query="import", path="agents", limit=5)

    # Check that it returns exactly 5 lines (headers are separate)
    # The current formatter returns a string with "match" on each line it finds
    # Let's check for the presence of ":" which usually separates file:line or file:match
    # Actually, let's just count how many matches it found
    assert results.count("import") == 5


def test_search_files_no_limit():
    # Small directory, should find all matches if limit is high enough
    results = search_files(query="PlanReport", path="agents/schema", limit=100)
    assert results.count("PlanReport") >= 1
