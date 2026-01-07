# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-01-07

### Added

- **GitHub Issue Planning**: Integrated `workflows/plan.py` to directly fetch and plan from GitHub issues (#88, #89).
- **Centralized Internet Search**: Implemented DuckDuckGo integration and added `internet_search` tool (#74, #83).
- **Documentation Hardening**: Enhanced fetching with Playwright/Jina AI and added paging (#75, #90).
- **Observability**: Integrated Langfuse for tracing DSPy and LLM calls (#81).
- **Release Automation**: Fixed CI permission issues for automated release tagging (#95).

### Fixed

- **Security**: Addressed CodeQL alerts for URL sanitization and potential substring attacks.
- **Code Quality**: Resolved empty except blocks, unused imports, and merge conflicts in development branch.
- **Review Workflow**: Fixed import inconsistencies and generalized reviewer discovery.

### Contributors

- **@Dan-StrategicAutomation**: Core infrastructure, Issue Planning, Observability, and Security Fixes.
- **@saksham-jain177**: Feat: Centralized internet search tool for research agents (#74, #83).
- **@hr1juldey**: Feat: MxBai embedding support (#79).
- **@Priya-Yanamandra**: Docs: Mkdocstrings API documentation for config module (#90).
- **GitHub Issue Planning**: The `plan` command now accepts GitHub issue IDs or URLs (e.g., `compounding plan 30`).
- **Documentation Paging**: Token-based pagination for large documentation with `offset_tokens` support.
- **Search Limits**: Added `limit` argument to `search_codebase` tool (default 50 results).
- **LRU Cache**: In-memory caching for documentation fetches to reduce API calls.
- **Internet Search Tool**: Integrated DuckDuckGo search for research agents.
- **Langfuse Integration**: Added observability and tracing for DSPy calls.
- **Generalize Review Context**: Added support for reviewing local branches, specific files, and unstaged changes (`latest`).

### Changed

- **Agent Filter Relaxations**: Allowed spaces in agent filters (e.g., "Docstring Checker").
- Simplified imports in `agents/schema/__init__.py`.
- Refactored `GitService.get_diff` into smaller helper methods for maintainability.
- Refactored `_gather_review_context` in `workflows/review.py` for reduced complexity.

### Fixed

- Safe config parsing with try/except for integer environment variables.
- Max pagination limit (10 pages) to prevent unbounded fetching.
- Removed dead code in `best_practices_researcher.py`.
- Pydantic recursion issues with safe model serialization.
- DuckDuckGo search import and dependency updates.
- Worktree creation logic for better local development support.

## [0.1.2] - 2025-12-30

### Added

- **Security Hardening**: Implemented PII scrubbing and safe command execution via `SecretScrubber`.
- **System Observability**: Standardized logging with `loguru` and introduced "quiet mode".
- **Automated Quality Control**: Integrated `ruff` for linting/formatting via pre-commit and CI.
- **Exhaustive Test Suite**: Added a comprehensive verification suite with over 80 passing tests.

### Fixed

- CodeQL security findings and hardened GitHub Actions workflow permissions.
- Various "empty except" blocks and ratio validation bugs in CLI and planning modules.

## [0.1.1-alpha] - 2025-12-22

### Added

- **Smart Context Gathering**: Enhanced project context analysis for better agent awareness.
- **Hybrid Search**: Implemented sparse embeddings using FastEmbed for knowledge base retrieval.
- **Codebase Indexing**: Added semantic search capabilities across the entire repository.
- **Vector Search Support**: Integrated Qdrant for efficient vector storage and retrieval.

### Changed

- Refactored review agents to use Pydantic signatures for better type safety and reliability.
- Organized utility modules into a structured `utils/` package.
- Renamed project to `dspy-compounding-engineering`.

## [0.1.0-alpha] - 2025-12-20

### Added

- Initial implementation of DSPy-based compounding engineering.
- Basic code review and research workflows.
- Core CLI framework for project interaction.
- Basic support for OpenAI and OpenRouter models.

---

[0.1.3]: https://github.com/Strategic-Automation/dspy-compounding-engineering/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Strategic-Automation/dspy-compounding-engineering/compare/v0.1.1-alpha...v0.1.2
[0.1.1-alpha]: https://github.com/Strategic-Automation/dspy-compounding-engineering/compare/v0.1.0-alpha...v0.1.1-alpha
