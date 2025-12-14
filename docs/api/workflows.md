# Workflows API Reference

Workflows orchestrate multi-step processes by coordinating agents, managing state, and handling user interaction.

## Core Workflows

### review.py

**Function**: `run_review(pr_url_or_id: str, project: bool = False)`

Orchestrates multi-agent code review.

**Process**:
1. Determine review scope (PR diff, branch diff, or full project)
2. Gather code via `GitService` or `ProjectContext`
3. Initialize Knowledge Base
4. Spawn review agents in parallel using `ThreadPoolExecutor`
5. Collect structured `ReviewReport` objects (Pydantic models) from agents
6. Parse findings and unique sections (e.g., `Risk Matrix`)
7. Create `*-pending-*.md` todo files for each finding, preserving full report context
8. Display summary table and codify learnings

**Configuration**:
Agents are registered in `workflows/review.py`.
```python
review_agents = [
    ("Kieran Rails Reviewer", KieranRailsReviewer),
    ("Security Sentinel", SecuritySentinel),
    # ...
]
```

**Output**: Markdown-formatted Todo files in `todos/` directory.

---

### triage.py

**Function**: `run_triage()`

Interactive UI for processing code review findings.

**Process**:
1. Load all `*-pending-*.md` files from `todos/`
2. Present each finding with file/line context
3. Prompt user: `[y]es / [n]ext / [a]ll / [c]ustom / [q]uit`
4. Convert approved findings to `*-ready-*.md`
5. Log decisions to `.work_log`
6. Generate next-steps instructions

**State Management**:
- Approved → `*-ready-*.md`
- Rejected → Deleted
- Modified → Updated in place with new priority/description

**KB Integration**: Captures triage decisions as learnings (future enhancement)

---

### work_unified.py

**Function**: `run_unified_work(pattern: str, dry_run: bool, parallel: bool, max_workers: int, in_place: bool)`

Unified command for resolving todos or executing plans.

**Input Detection**:
```python
if pattern.endswith('.md') and 'plans/' in pattern:
    mode = 'plan_execution'
elif pattern.isdigit() or pattern in ['p1', 'p2', 'p3']:
    mode = 'todo_resolution'
else:
    mode = 'pattern_search'
```

**Execution Flow**:
1. **Pattern Matching**: Find todos matching pattern
2. **Context Loading**: Get project context + KB learnings
3. **Worktree Creation** (if `--worktree`): Isolate execution
4. **Agent Execution**:
   - Sequential: Process one by one
   - Parallel: Use `ThreadPoolExecutor` with `max_workers`
5. **Verification**: Run tests (if configured)
6. **Codification**: Extract and save learnings
7. **Cleanup**: Remove worktrees, mark todos complete

**Dry Run Mode**: Simulates execution without file writes

**Parallel Safety**: Uses file locks and thread-safe git operations

---

### plan.py

**Function**: `run_plan(feature_description: str)`

Generates implementation plans from natural language.

**Process**:
1. Gather project context (README, file tree, key configs)
2. Retrieve relevant KB learnings (architecture decisions)
3. Use `TaskPlanner` agent to generate markdown plan
4. Save to `plans/<slugified-description>.md`
5. Display plan path and summary

**Plan Format**:
```markdown
# Feature: <description>

## Context
<Background and goals>

## Proposed Changes
### Component 1
- File: path/to/file.py
  - Change: Description of modification

## Verification Plan
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing steps
```

---

### codify.py

**Function**: `run_codify(feedback: str, source: str = "manual_input")`

Converts natural language feedback into structured learnings.

**Process**:
1. Use `FeedbackCodifier` agent to structure the input
2. Extract: context, action, rationale, tags, category
3. Generate unique learning ID
4. Save to `.knowledge/learnings/<id>.json`
5. Update `AI.md` with new learning
6. Display confirmation

**Example**:
```bash
uv run python cli.py codify "Use async/await for all I/O operations" --source architecture_review
```

Creates:
```json
{
  "id": "uuid",
  "timestamp": "2025-12-07T10:00:00Z",
  "source": "architecture_review",
  "context": "When performing I/O operations in Python",
  "action": "Use async/await syntax",
  "rationale": "Improves performance and scalability",
  "tags": ["performance", "async", "python"],
  "category": "best_practice"
}
```

---

### generate_command.py

**Function**: `run_generate_command(description: str, dry_run: bool = False)`

Meta-command to generate new CLI commands from natural language.

**Process**:
1. Analyze the description to understand intent
2. Design appropriate workflow structure
3. Identify required agents/signatures
4. Generate code for:
   - CLI command in `cli.py`
   - Workflow in `workflows/`
   - Agent signatures if needed
5. Write files (or show preview if `--dry-run`)

**Example**:
```bash
uv run python cli.py generate-command "Create a command to format all Python files"
```

Generates:
- `workflows/format_code.py`
- CLI entry in `cli.py`

---

## Shared Utilities

All workflows use these common patterns:

### Knowledge Base Integration
```python
from utils.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
learnings = kb.retrieve_relevant(query="security review", max_results=5)
# Pass learnings to agents
```

### Git Operations
```python
from utils.git_service import GitService

# Get diff
diff = GitService.get_diff("HEAD")

# Create worktree
GitService.create_feature_worktree("feature-x", "worktrees/feature-x")
```

### Project Context
```python
from utils.project_context import ProjectContext

context = ProjectContext(base_dir=".").get_context()
# Returns: README + pyproject.toml + file tree
```

### Todo Service
```python
from utils.todo_service import create_finding_todo, complete_todo

# Create
todo_path = create_finding_todo(finding_dict, todos_dir="todos")

# Complete
complete_todo(todo_path, outcome="fixed", learnings=["..."])
```

## Error Handling

All workflows implement consistent error handling:

```python
try:
    # Workflow logic
    result = execute_task()
except subprocess.CalledProcessError as e:
    console.print(f"[red]Git operation failed: {e}[/red]")
    sys.exit(1)
except Exception as e:
    console.print(f"[red]Unexpected error: {e}[/red]")
    # Cleanup (remove worktrees, restore state)
    sys.exit(1)
```

## Adding New Workflows

Template:
```python
from rich.console import Console
from utils.knowledge_base import KnowledgeBase

console = Console()

def run_my_workflow(arg1: str, arg2: bool = False):
    \"\"\"
    Description of what this workflow does.
    \"\"\"
    # 1. Setup
    kb = KnowledgeBase()
    
    # 2. Get KB context
    context = kb.retrieve_relevant("my workflow")
    
    # 3. Execute agents
    agent = MyAgent(kb=kb)
    result = agent.execute(arg1, context=context)
    
    # 4. Handle result
    if result.success:
        console.print("[green]Success![/green]")
        # 5. Codify learnings
        kb.save_learning(result.learning)
    else:
        console.print("[red]Failed[/red]")
        return False
    
    return True
```

Then add to `cli.py`:
```python
@app.command()
def my_workflow(arg1: str, arg2: bool = False):
    \"\"\"CLI docstring\"\"\"
    run_my_workflow(arg1, arg2)
```
