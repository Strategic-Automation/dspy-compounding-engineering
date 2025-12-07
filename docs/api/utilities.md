# Utilities API Reference

Utilities provide cross-cutting functionality used by workflows and agents.

## git_service.py

**Class**: `GitService`

Handles Git and GitHub CLI operations.

### Methods

#### `is_git_repo() -> bool`
Check if current directory is a Git repository.

```python
if GitService.is_git_repo():
    print("In a git repo")
```

#### `get_diff(target: str = "HEAD") -> str`
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

#### `get_current_branch() -> str`
Get the current branch name.

#### `create_feature_worktree(branch_name: str, worktree_path: str) -> None`
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

#### `checkout_pr_worktree(pr_id_or_url: str, worktree_path: str) -> None`
Checkout a PR into an isolated worktree (requires `gh` CLI).

**Limitations**: Struggles with PRs from forks (known issue)

---

## project_context.py

**Class**: `ProjectContext`

Gathers project information for AI context.

### Methods

#### `__init__(base_dir: str = ".")`
Initialize with a base directory.

#### `get_context() -> str`
Get basic project context (README, configs, file list).

**Returns**: Concatenated string of key files (first 1000 chars each)

**Example**:
```python
context = ProjectContext().get_context()
# Use in agent prompts for project awareness
```

#### `gather_project_files(max_file_size: int = 50000) -> str`
Gather all relevant code files for full project review.

**Parameters**:
- `max_file_size`: Max characters per file (truncates if larger)

**Supported Extensions**:
- Code: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.rb`, `.go`, `.rs`, `.java`, `.kt`
- Config: `.toml`, `.yaml`, `.yml`, `.json`

**Returns**: Concatenated file contents with headers

**Example**:
```python
project_code = ProjectContext().gather_project_files(max_file_size=10000)
agent.review(code=project_code)
```

---

## knowledge_base.py

**Class**: `KnowledgeBase`

Core of the compounding engineering system.

### Methods

#### `__init__(knowledge_dir: str = ".knowledge")`
Initialize KB storage.

#### `save_learning(learning: dict) -> str`
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

#### `retrieve_relevant(query: str, tags: List[str] = None, max_results: int = 5) -> List[dict]`
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

#### `update_ai_md() -> None`
Regenerate the human-readable `AI.md` summary from all learnings.

**Called automatically** after `save_learning()`.

---

## todo_service.py

**Functions for todo file management**

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

**Example**:
```python
add_work_log_entry(
    "[2025-12-07] Fixed SQL injection in auth.py via prepared statements"
)
```

---

## kb_module.py

**Class**: `KBPredict`

DSPy wrapper that auto-injects Knowledge Base context.

### Usage

```python
from utils.kb_module import KBPredict
from utils.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Instead of dspy.Predict
predictor = KBPredict("code, context -> review", kb=kb)

# KB context is automatically injected
result = predictor(code="def foo(): pass")
# 'context' field is auto-populated from kb.retrieve_relevant()
```

**How It Works**:
1. Intercepts `forward()` call
2. Generates KB query from input kwargs
3. Retrieves relevant learnings
4. Injects as `context` parameter
5. Calls parent `dspy.Predict`

---

## file_tools.py

**Functions for safe file operations**

### `safe_read(path: str) -> str`
Read a file with error handling.

**Returns**: File contents or empty string on error

### `safe_write(path: str, content: str, backup: bool = True) -> bool`
Write to a file with optional backup.

**Parameters**:
- `path`: File to write
- `content`: Content to write
- `backup`: Create `.bak` backup before writing

**Returns**: True if successful

### `apply_line_edit(file_path: str, start_line: int, end_line: int, new_content: str) -> bool`
Apply a line-based edit to a file.

**Parameters**:
- `file_path`: File to edit
- `start_line`: 1-indexed start line
- `end_line`: 1-indexed end line (inclusive)
- `new_content`: Replacement content

**Returns**: True if successful

**Example**:
```python
# Replace lines 10-12 with new function
apply_line_edit(
    "src/utils.py",
    start_line=10,
    end_line=12,
    new_content="def new_function():\n    pass\n"
)
```

---

## learning_extractor.py

**Class**: `LearningExtractor`

Automatically extracts learnings from completed work.

### Methods

#### `extract_from_todo(todo_path: str, git_diff: str, test_results: str = None) -> List[dict]`
Analyze a completed todo and extract learnings.

**Process**:
1. Read todo description and context
2. Parse git diff to see what changed
3. Use AI to identify patterns/lessons
4. Structure as learnings

**Returns**: List of learning dicts

**Example**:
```python
extractor = LearningExtractor(kb=kb)
learnings = extractor.extract_from_todo(
    todo_path="todos/001-complete-fix-sql-injection.md",
    git_diff=diff,
    test_results="All tests passed"
)

for learning in learnings:
    kb.save_learning(learning)
```

---

## safe_io.py

**Context managers for safe I/O**

### `atomic_write(path: str, mode: str = "w")`
Context manager for atomic file writes (write to temp, then move).

**Example**:
```python
from utils.safe_io import atomic_write

with atomic_write("important.json") as f:
    json.dump(data, f)
# File only replaced if no exception occurred
```

---

## Common Patterns

### Workflow Initialization
```python
from utils.knowledge_base import KnowledgeBase
from utils.project_context import ProjectContext
from utils.git_service import GitService

kb = KnowledgeBase()
context = ProjectContext().get_context()
diff = GitService.get_diff("HEAD")
```

### KB-Augmented Agent Call
```python
learnings = kb.retrieve_relevant("security review")
result = agent.review(code=code, context=learnings)
```

### Safe Worktree Workflow
```python
worktree = f"worktrees/{task_id}"
try:
    GitService.create_feature_worktree(f"task/{task_id}", worktree)
    # Do work in worktree
    os.chdir(worktree)
    execute_task()
finally:
    os.chdir(original_dir)
    subprocess.run(["git", "worktree", "remove", worktree])
```
