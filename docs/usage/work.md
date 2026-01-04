# Work Execution

The `work` command is the core engine of the Compounding Engineering system. It executes tasks using AI agents that can read files, search code, and apply edits. It unifies todo resolution and plan execution into a single robust workflow.

## Usage

```bash
compounding work [PATTERN] [OPTIONS]
```

### Arguments

- `PATTERN`: (Optional) Specifies what to work on. Can be:
    -   **Todo ID**: e.g., `001`, `123`
    -   **Plan File**: e.g., `plans/feature_x.md`
    -   **Keyword/Tag**: e.g., `p1` (priority 1), `security`, `bug`
    -   If omitted, it defaults to working on available high-priority todos.

### Options

- `--dry-run` / `-n`: Simulate the work without writing any changes to disk. Useful for checking what the agents would do.
- `--sequential` / `-s`: Run tasks one by one. By default, tasks run in parallel.
- `--workers` / `-w`: Set the number of parallel workers (default: 3).
- `--in-place` / `--worktree`: Choose execution mode:
    -   `--in-place` (Default): Modifies files in your current directory.
    -   `--worktree`: Creates a temporary git worktree for complete isolation.

## Examples

### 1. Resolve Specific Items

```bash
# Work on a specific todo
compounding work 001

# Execute a plan
compounding work plans/auth_system.md
```

### 2. Batch Processing

```bash
# Work on all 'High Priority' (P1) items in parallel
compounding work p1

# Work on security-related items
compounding work security
```

### 3. Safe Mode

```bash
# Run in an isolated worktree to prevent messing up your current state
compounding work p1 --worktree

# Preview what would happen
compounding work 001 --dry-run
```

## How It Works

1.  **Selection**: Finds todos or plan items matching your pattern.
2.  **Knowledge Injection**: Automatically fetches relevant past learnings from the `KnowledgeBase` and injects them into the agent's context.
3.  **Smart Context**: Uses `ProjectContext` and `RelevanceScorer` to gather the most relevant files while strictly adhering to the LLM's token budget.
4.  **Agent Execution**:
    -   **ReAct Loop**: The agent "Thinks", "Acts" (uses tools), and "Observes" results.
    -   **Tools**: It can `search`, `read_file`, `edit_file`, and `run_test`.
    -   **Self-Correction**: If an edit fails or a test breaks, it iterates to fix it.
5.  **Completion**: Updates the mapping file (e.g., `todos/123-ready-*.md` -> `todos/123-complete-*.md`).
6.  **Codification**: Automatically extracts new learnings from the session and saves them to the Knowledge Base, compounding the system's intelligence.

## Parallel Execution

The system uses Python's `ThreadPoolExecutor` to run multiple agents simultaneously.
-   **Thread Safety**: File operations are locked where necessary.
-   **Output**: Logs are interleaved in the console, but the final summary shows per-task results.
