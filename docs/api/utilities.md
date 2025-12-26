# Utilities API Reference

Utilities provide cross-cutting functionality used by workflows and agents.

## utils.git

**Package**: `utils.git`

The `utils.git` package provides the `GitService` class for interacting with git repositories and GitHub.

### `GitService`

Handles Git and GitHub CLI operations.

#### Methods

##### `is_git_repo() -> bool`
Check if current directory is a Git repository.

```python
if GitService.is_git_repo():
    print("In a git repo")
```

##### `get_diff(target: str = "HEAD") -> str`
Get git diff for a target commit, branch, or PR.

**Parameters**:
- `target`: Commit SHA, branch name, PR URL, or PR number

**Returns**: Diff string

**Example**:
```python
# Local changes
diff = GitService.get_diff("HEAD")

# PR from GitHub
diff = GitService.get_diff("https://github.com/owner/repo/pull/123")
```

##### `get_current_branch() -> str`
Get the current branch name.

##### `create_feature_worktree(branch_name: str, worktree_path: str) -> None`
Create a git worktree for a feature branch.

**Example**:
```python
GitService.create_feature_worktree(
    branch_name="feature/auth",
    worktree_path="worktrees/auth"
)
# Now work in worktrees/auth/ directory
```

**Behavior**:
- If branch exists: Checks it out in worktree
- If new: Creates branch and worktree from HEAD

##### `checkout_pr_worktree(pr_id_or_url: str, worktree_path: str) -> None`
Checkout a PR into an isolated worktree (requires `gh` CLI).

**Limitations**: Struggles with PRs from forks (known issue)

---

## utils.context

**Package**: `utils.context`

The `utils.context` package provides project context analysis.

### `ProjectContext`

Gathers project information for AI context.

#### Methods

##### `__init__(base_dir: str = ".")`
Initialize with a base directory.

##### `get_context() -> str`
Get basic project context (README, configs, file list).

**Returns**: Concatenated string of key files (first 1000 chars each)

**Example**:
```python
context = ProjectContext().get_context()
# Use in agent prompts for project awareness
```

##### `gather_smart_context(task: str = "", budget: int = 124000) -> str`
Gather project files intelligently, prioritizing relevance to a task and respecting a token budget.

**Parameters**:
- `task`: Task description for relevance scoring
- `budget`: Token limit (default configured by `CONTEXT_WINDOW_LIMIT`)

**Features**:
- **Relevance Scoring**: Prioritizes files relevant to `task` (keywords, semantics) + Tier 1 files (README, config).
- **Token Budgeting**: Stops adding files when budget is reached.

**Example**:
```python
ctx = ProjectContext()
# Get context for fixing a bug in auth
context = ctx.gather_smart_context(task="Fix authentication bug", budget=50000)
```

##### `gather_project_files(max_file_size: int = 50000) -> str`
*Legacy alias* for `gather_smart_context(task="", ...)`

**Parameters**:
- `max_file_size`: Max characters per file (truncates if larger)

**Supported Extensions**:
- Code: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.rb`, `.go`, `.rs`, `.java`, `.kt`
- Config: `.toml`, `.yaml`, `.yml`, `.json`
- **Tier 1**: `README.md`, `pyproject.toml`, etc. are always considered.

**Returns**: Concatenated file contents with headers

---

## utils.knowledge

**Package**: `utils.knowledge`

Core of the compounding engineering system.

### `KnowledgeBase`

#### Methods

##### `__init__(knowledge_dir: str = ".knowledge")`
Initialize KB storage.

##### `save_learning(learning: dict) -> str`
Save a structured learning to disk.

**Learning Schema**:
```python
{
    "id": "uuid",
    "timestamp": "ISO-8601",
    "source": "work|review|triage|manual",
    "context": "When ...",
    "action": "Do ...",
    "rationale": "Because ...",
    "tags": ["tag1", "tag2"],
    "category": "best_practice|pattern|gotcha|..."
}
```

**Returns**: Learning ID

##### `retrieve_relevant(query: str, tags: List[str] = None, max_results: int = 5) -> List[dict]`
Retrieve learnings relevant to a query.

**Current Implementation**: Keyword matching

**Parameters**:
- `query`: Search keywords (e.g., "authentication security")
- `tags`: Filter by specific tags
- `max_results`: Max learnings to return

**Returns**: List of learning dicts, sorted by relevance

**Example**:
```python
kb = KnowledgeBase()
learnings = kb.retrieve_relevant("database migrations", tags=["database"])
for l in learnings:
    print(f"{l['action']} - {l['rationale']}")
```

##### `update_ai_md() -> None`
Regenerate the human-readable `AI.md` summary from all learnings.

**Called automatically** after `save_learning()`.

### `KBPredict`

DSPy wrapper that auto-injects Knowledge Base context.

#### Usage

```python
from utils.knowledge import KnowledgeBase, KBPredict

kb = KnowledgeBase()

# Instead of dspy.Predict
predictor = KBPredict("code, context -> review", kb=kb)

# KB context is automatically injected
result = predictor(code="def foo(): pass")
# 'context' field is auto-populated from kb.retrieve_relevant()
```

---

## utils.todo

**Package**: `utils.todo`

Manages the file-based todo system.

### `create_finding_todo(finding: dict, todos_dir: str = "todos") -> str`
Create a `*-pending-*.md` file from a review finding.

**Parameters**:
- `finding`: Dict with keys: `agent`, `severity`, `description`, `file_path`, `line_number`, `recommendation`
- `todos_dir`: Directory to save in

**Returns**: Path to created file

**Filename Pattern**: `{id}-pending-{agent}-{slugified-desc}.md`

### `complete_todo(todo_path: str, outcome: str = "fixed", learnings: List[str] = None) -> str`
Mark a todo as complete.

**Parameters**:
- `todo_path`: Path to `*-ready-*.md` or `*-pending-*.md`
- `outcome`: "fixed", "wont-fix", "duplicate"
- `learnings`: List of extracted learnings

**Returns**: New path to `*-complete-*.md` file

**Side Effects**:
- Appends to `.work_log`
- Saves learnings to KB

### `add_work_log_entry(entry: str, log_path: str = ".work_log") -> None`
Append an entry to the work log.

---

## utils.io

**Package**: `utils.io`

Functions for safe file operations.

### `read_file_range(file_path: str, start_line: int, end_line: int) -> str`
Read specific lines from a file.

### `safe_write(path: str, content: str, base_dir: str = ".") -> None`
Safely write content to a file, preventing path traversal.

### `edit_file_lines(file_path: str, edits: List[Dict]) -> str`
Edit specific lines in a file.

### `list_directory(path: str, base_dir: str = ".") -> str`
List files in a directory.

---

## Common Patterns

### Workflow Initialization
```python
from utils.knowledge import KnowledgeBase
from utils.context import ProjectContext
from utils.git import GitService

kb = KnowledgeBase()
context = ProjectContext().get_context()
diff = GitService.get_diff("HEAD")
```

### KB-Augmented Agent Call
```python
learnings = kb.retrieve_relevant("security review")
result = agent.review(code=code, context=learnings)
```
