## Pull Request

### Description

This PR finalizes the codebase for the v0.1.3 release by addressing remaining linting errors, centralizing configuration constants, and ensuring all tests pass.

### Type of Change

- [x] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [x] 📝 Documentation update
- [x] ♻️ Code refactoring
- [x] ⚡ Performance improvement
- [x] ✅ Test addition or update

### Changes Made

- **Centralized Configuration**: Moved scattered hardcoded constants (timeouts, limits, URLs) into `AppConfig` in `config.py`.
- **Linting Fixes**: Resolved all remaining Ruff errors, including line lengths (E501) and complexity (C901) in `utils/context/project.py`.
- **Changelog**: Updated `CHANGELOG.md` with v0.1.3 details.
- **Complexity Reduction**: Refactored `_collect_context_candidates` to be more readable.

### Related Issues

Relates to v0.1.3 release release.

### Testing

- [x] All existing tests pass
- [ ] Added new tests for new functionality
- [x] Manually tested the changes
- [x] Updated documentation

#### Test Commands Run

```bash
uv run pytest
uv run ruff check .
```

### Documentation

- [x] Updated relevant documentation in `docs/` (Changelog)
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

N/A

### Additional Notes

This prepares the `dev` branch for the v0.1.3 release tag.
