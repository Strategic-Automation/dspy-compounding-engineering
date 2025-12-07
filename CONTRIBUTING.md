# Contributing

Thank you for your interest in contributing to Compounding Engineering! This project thrives on community contributions.

## Ways to Contribute

- 🐛 **Report bugs** - Help us identify issues
- 💡 **Suggest features** - Share ideas for improvements
- 📝 **Improve documentation** - Help others understand the project
- 🔧 **Submit code** - Fix bugs or add features
- ⭐ **Share knowledge** - Contribute review agents or workflow improvements

> **Looking for something to do?** Check out our [Issues page](https://github.com/Strategic-Automation/dspy-compounding-engineering/issues) for open tasks!

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/dspy-compounding-engineering.git
cd dspy-compounding-engineering
```

### 2. Set Up Development Environment

```bash
# Install dependencies including dev tools
uv sync --group dev

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agents --cov=workflows --cov=utils

# Run specific tests
uv run pytest tests/test_knowledge_base.py -v
```

### Linting and Formatting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Running the CLI Locally

```bash
# Use uv run for development
uv run python cli.py review --help

# Or activate the venv
source .venv/bin/activate
python cli.py review
```

## Project Structure

```
dspy-compounding-engineering/
├── agents/              # DSPy agent signatures and modules
│   ├── review/          # Code review agents
│   ├── workflow/        # Work execution agents
│   └── research/        # Repository research agents
├── workflows/           # High-level workflow orchestration
│   ├── review.py
│   ├── triage.py
│   ├── work_unified.py
│   └── plan.py
├── utils/               # Shared utilities
│   ├── knowledge_base.py
│   ├── git_service.py
│   └── todo_service.py
├── docs/                # MkDocs documentation
├── tests/               # Test suite
└── cli.py               # CLI entry point
```

## Adding a New Review Agent

Review agents are specialized code reviewers. Here's how to add one:

### 1. Create the Agent File

Create `agents/review/your_agent_name.py`:

```python
import dspy

class YourAgentReviewer(dspy.Signature):
    \"\"\"Specialized review agent for [specific concern]\"\"\"
    
    file_path: str = dspy.InputField(desc="Path to the file being reviewed")
    file_content: str = dspy.InputField(desc="Content of the file")
    context: str = dspy.InputField(desc="Additional context from knowledge base")
    
    finding: str = dspy.OutputField(
        desc="Detailed finding with severity, issue, and recommendation"
    )
```

### 2. Register in `agents/review/__init__.py`

```python
from .your_agent_name import YourAgentReviewer

REVIEW_AGENTS = [
    # ... existing agents ...
    ("Your Agent Name", YourAgentReviewer),
]
```

### 3. Add Tests

Create `tests/test_your_agent.py`:

```python
import dspy
from agents.review.your_agent_name import YourAgentReviewer

def test_your_agent_reviewer():
    # Test your agent logic
    pass
```

### 4. Update Documentation

Add your agent to `docs/usage/review.md`.

## Pull Request Process

### 1. Write Good Commit Messages

```bash
# Good
git commit -m "feat: Add performance review agent for database queries"
git commit -m "fix: Handle missing .env file gracefully"
git commit -m "docs: Update installation guide for Windows"

# Follow conventional commits
# feat: | fix: | docs: | test: | refactor: | chore:
```

### 2. Create a Pull Request

- Write a clear title and description
- Reference any related issues (#123)
- Explain what changed and why
- Include screenshots for UI changes
- Ensure all tests pass

### 3. Code Review

- Respond to feedback constructively
- Make requested changes
- Update your PR branch if needed

### 4. Merge

Once approved, a maintainer will merge your PR!

## Testing Guidelines

### Unit Tests

Test individual functions and classes:

```python
def test_knowledge_base_save():
    kb = KnowledgeBase()
    learning = {
        "category": "test",
        "summary": "Test learning",
        "content": "Test content"
    }
    kb.save(learning)
    assert kb.retrieve("test") is not None
```

### Integration Tests

Test workflows end-to-end:

```python
def test_review_workflow(tmp_path):
    # Create a test repository
    # Run review workflow
    # Assert findings are generated
    pass
```

## Documentation

Documentation is built with MkDocs. To preview locally:

```bash
uv run mkdocs serve
# Open http://127.0.0.1:8000
```

Update documentation in `docs/` when adding features.

## Code Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints where appropriate
- Write docstrings for public functions
- Keep functions focused and small
- Prefer readability over cleverness

## Questions?

- **Issues**: [GitHub Issues](https://github.com/Strategic-Automation/dspy-compounding-engineering/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Strategic-Automation/dspy-compounding-engineering/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Compounding Engineering! 🎉
