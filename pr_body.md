## Pull Request

### Description
This PR adds automatic GitHub issue creation for critical (P1) review findings. When the review workflow identifies critical issues, it will automatically create GitHub issues to ensure they are tracked and addressed promptly.

### Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [x] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] ♻️ Code refactoring
- [ ] ⚡ Performance improvement
- [ ] ✅ Test addition or update

### Changes Made

- **GitService.create_issue()**: Added new static method in `utils/git/service.py` to create GitHub issues using the `gh` CLI
  - Accepts title, body, and optional labels
  - Returns issue URL and number
  - Validates `gh` CLI is installed before attempting creation
  
- **_create_review_issues()**: Added new function in `workflows/review.py` to automatically create GitHub issues for critical findings
  - Only creates issues for P1 (critical) severity findings
  - Skips findings with errors or no action required
  - Applies appropriate labels: category, severity, and "automated-review"
  - Displays created issue URLs in the console output

- **Review Workflow Integration**: Updated `run_review()` to call `_create_review_issues()` after creating todos (step 5), with subsequent steps renumbered

### Related Issues

Closes #
Related to #

### Testing

- [x] All existing tests pass
- [ ] Added new tests for new functionality
- [x] Manually tested the changes
- [ ] Updated documentation

#### Test Commands Run
```bash
# Run all tests
uv run pytest tests/ -v

# Run linting
uv run ruff check .

# Test review workflow
uv run python cli.py review <pr-url> --dry-run
```

### Documentation

- [ ] Updated relevant documentation in `docs/`
- [ ] Updated README.md (if applicable)
- [ ] Updated docstrings and type hints
- [x] No documentation changes needed

### Checklist

- [x] My code follows the project's code style
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes

### Screenshots (if applicable)
N/A - Backend/CLI changes only

### Additional Notes

**Prerequisites:**
- Requires GitHub CLI (`gh`) to be installed and authenticated
- The `gh` CLI must have permissions to create issues in the target repository

**Behavior:**
- Only P1 (critical) findings trigger automatic issue creation
- Issues are labeled with:
  - The finding category (e.g., `security`, `performance`)
  - Severity level (`severity:p1`)
  - `automated-review` tag for tracking

**Example Issue Created:**
```
Title: CRITICAL: SecuritySentinel Finding
Body:
## SecuritySentinel Review Finding

[Review content here]

**Category:** security
**Severity:** P1
```

**Future Enhancements:**
- Add configuration option to control which severity levels create issues
- Add option to assign issues to specific team members
- Add duplicate detection to avoid creating duplicate issues for the same finding
