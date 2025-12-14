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

1.  **SecuritySentinel**: Looks for vulnerabilities and creates a Risk Matrix.
2.  **PerformanceOracle**: Checks for O(n^2) loops, N+1 queries, and suggests optimizations.
3.  **ArchitectureStrategist**: Validates design patterns and SOLID principles.
4.  **DataIntegrityGuardian**: Checks validation logic, privacy compliance, and migration safety.
5.  **DhhRailsReviewer**: Enforces standard Rails conventions and DHH-style simplicity.
6.  **CodeSimplicityReviewer**: Focuses on reducing necessary complexity.
7.  **PatternRecognitionSpecialist**: Identifies design patterns and anti-patterns.
8.  **Kieran Reviewers**: Specialized agents (Rails, Python, TS) enforcing team-specific standards.

## Knowledge Base Integration

Every agent automatically receives context from the Knowledge Base.
-   *Example*: If you previously codified "Always use `logger.error` instead of `print`", the `KieranPythonReviewer` will catch violations in future reviews.

## Output

The findings are saved as structured **Markdown Todo files** in the `todos/` directory. 
Each file contains:
- Executive Summary & Technical Analysis
- Detailed Findings with Severity & Category
- Unique Agent Metrics (e.g., Risk Matrix, Typesafety Score)
- Proposed Solutions & Effort Estimates

You use the `triage` command to process them.
