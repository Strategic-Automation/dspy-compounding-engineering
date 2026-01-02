# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-01-02

### Added
- **Internet Search Tool**: Integrated DuckDuckGo search for research agents.
- **Dynamic Agent Discovery**: Implemented automatic discovery and generation of specialized agents.
- **Langfuse Integration**: Added observability and tracing for DSPy calls.
- **Generalize Review Context**: Added support for reviewing local branches, specific files, and unstaged changes (`latest`).

### Fixed
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
