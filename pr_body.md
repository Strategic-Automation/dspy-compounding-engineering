## Pull Request

### Description
This PR implements high-fidelity documentation fetching using Playwright as a fallback mechanism, along with significant code simplification and hardening across the codebase. The changes improve documentation fetching reliability for JavaScript-heavy documentation sites while removing unnecessary complexity from configuration, workflows, and utility modules.

### Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [x] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [x] ♻️ Code refactoring
- [x] ⚡ Performance improvement
- [ ] ✅ Test addition or update

### Changes Made

- **Playwright Integration**: Added Playwright as a dependency for high-fidelity documentation fetching with JS rendering support
- **Documentation Fetcher Refactoring**: Simplified `DocumentationFetcher` by removing token-based pagination, LRU caching, and complex truncation logic in favor of a cleaner three-tier fallback approach (Jina AI → Playwright → Local parsing)
- **Configuration Simplification**: Streamlined `config.py` by removing unused settings and simplifying the configuration structure
- **Workflow Optimization**: Simplified `workflows/plan.py` and `workflows/review.py` with cleaner context handling
- **Git Service Improvements**: Refactored `utils/git/service.py` for better maintainability
- **File I/O Hardening**: Simplified `utils/io/files.py` with improved error handling
- **Knowledge Base Updates**: Enhanced `utils/knowledge/embeddings.py` with better embedding support
- **Test Cleanup**: Removed outdated tests (`test_documentation_paging.py`, `test_integration_llm.py`, `test_search_limit.py`) and added new `test_documentation_fetcher.py`

### Related Issues

Closes #75
Related to #87

### Testing

- [x] All existing tests pass
- [x] Added new tests for new functionality
- [x] Manually tested the changes
- [x] Updated documentation

#### Test Commands Run
```bash
# Run all tests
uv run pytest tests/ -v

# Run linting
uv run ruff check .

# Test documentation fetcher specifically
uv run pytest tests/test_documentation_fetcher.py -v
```

### Documentation

- [x] Updated relevant documentation in `docs/`
- [x] Updated README.md (if applicable)
- [x] Updated docstrings and type hints
- [ ] No documentation changes needed

### Checklist

- [x] My code follows the project's code style
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] My changes generate no new warnings or errors
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes

### Screenshots (if applicable)
N/A - Backend changes only

### Additional Notes

**Key Architecture Changes:**
1. The documentation fetcher now uses a three-tier fallback strategy:
   - Primary: Jina AI reader for high-quality markdown conversion
   - Secondary: Playwright for JavaScript-heavy sites that need rendering
   - Tertiary: Local BeautifulSoup parsing as final fallback

2. Removed pagination/paging complexity from documentation fetching - the full document is now fetched and processed in one pass, which simplifies the API and reduces potential edge cases.

3. This PR includes changes from multiple merged feature branches including:
   - Internet search tool integration
   - Dynamic agent discovery
   - Langfuse observability
   - Generalized review context support

**Dependencies Added:**
- `playwright` (v1.57.0) - For headless browser-based documentation fetching

**Breaking Changes:**
- `DocumentationFetcher.fetch()` no longer accepts `max_tokens` or `offset_tokens` parameters
- Removed `settings.documentation_max_pages` and `settings.jina_reader_url` configuration options
