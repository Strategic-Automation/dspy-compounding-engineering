# Code Review

The `review` command orchestrates a team of specialized AI agents to review your code. Unlike a generic "LGTM" bot, this runs multiple distinct personas (Security, Performance, Architecture, etc.) in parallel to provide deep, multi-dimensional feedback.

## Usage

```bash
uv run python cli.py review [TARGET] [OPTIONS]
```

### Arguments

- `TARGET`: What to review. Defaults to `latest` (local uncommitted changes).
    -   `latest` / `local`: Reviews changes in your current working directory (git diff).
    -   `PR_ID` / `PR_URL`: Reviews a specific GitHub Pull Request (requires `gh` CLI).
    -   `BRANCH_NAME`: Reviews changes on a specific branch compared to main.

### Options

- `--project` / `-p`: Review the **entire project** code, not just the diff/changes. useful for initial audits or periodic deep scans.

## Examples

```bash
# Workflow 1: Pre-commit check (Local)
# Review changes I just made before committing
uv run python cli.py review

# Workflow 2: PR Review
# Review a pull request
uv run python cli.py review https://github.com/my/repo/pull/123

# Workflow 3: Full Audit
# Deep scan of the whole codebase
uv run python cli.py review --project
```

## The Agent Squad

The system runs several agents in parallel. Each looks for different things:

1.  **SecuritySentinel**: Looks for vulnerabilities (SQLi, XSS, insecure deps).
2.  **PerformanceOracle**: Checks for O(n^2) loops, N+1 queries, inefficient resource usage.
3.  **ArchitectureStrategist**: Validates design patterns, SOLID principles, and modularity.
4.  **DataIntegrityGuardian**: Checks validation logic, transaction boundaries, and schema consistency.
5.  **MaintainabilitySage**: Reviews naming conventions, complexity, and documentation.
6.  **TestCoverageWarden**: Ensures new code has appropriate tests.

## Knowledge Base Integration

Every agent automatically receives context from the Knowledge Base.
-   *Example*: If you previously codified "Always use `logger.error` instead of `print`", the `MaintainabilitySage` will catch violations in future reviews.

## Output

The findings are saved as structured JSON files in the `todos/` directory. You use the `triage` command to process them.
