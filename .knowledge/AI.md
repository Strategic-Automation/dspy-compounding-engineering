# AI Knowledge Base

This file contains codified learnings and improvements for the AI system.
It is automatically updated when new learnings are added.

## Automation

### Always use strict typing in Python files

**Improvements:**

- [CHECK] Enforce strict typing with mypy in CI/CD: Integrate mypy type checker into CI pipeline to fail builds on type errors, ensuring all Python files use strict typing (type hints on functions, variables, etc.)
- [CHECK] Add mypy pre-commit hook: Install mypy as a pre-commit hook to catch typing issues locally before commits
- [DOCUMENT] Add strict typing guideline: Document requirement for type hints in all Python modules to promote best practices
