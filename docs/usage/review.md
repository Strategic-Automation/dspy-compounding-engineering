# Code Review

The `review` command orchestrates a team of specialized AI agents to review your code. Unlike a generic "LGTM" bot, this runs multiple distinct personas (Security, Performance, Architecture, etc.) in parallel to provide deep, multi-dimensional feedback.

## Usage

```bash
compounding review [TARGET] [OPTIONS]
```

### Arguments

- `TARGET`: What to review. Defaults to `latest`.
    -   `latest` / `local`: Reviews changes in your current working directory (staged/unstaged).
    -   `86` (ID): Reviews PR #86.
    -   `https://.../pull/86` (URL): Reviews the specific PR.
    -   `dev` (Branch): Reviews the `dev` branch vs `main`.

### Options

- `--project` / `-p`: Review the **entire project** code, not just the diff/changes. useful for initial audits or periodic deep scans.
- `--agent` / `-a`: Filter which agents run during the review. You can provide a specific agent name (e.g., `SecuritySentinel`) or a pattern.
    
### Default Exclusions

The review process automatically ignores the following:
- **Directories**: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `dist`, `build`, `.tox`, `.mypy_cache`, `.ruff_cache`
- **Files**: `uv.lock`, `package-lock.json`, `yarn.lock`, `poetry.lock`, `Gemfile.lock`

## Examples

```bash
# Workflow 1: Pre-commit check (Local)
# Review changes I just made before committing
compounding review

# Workflow 2: PR Review
# Review a pull request
compounding review https://github.com/my/repo/pull/123

# Workflow 3: Full Audit
# Deep scan of the whole codebase
compounding review --project
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

The review provides real-time feedback in the console using a clean, parallel progress interface. 

### Local Storage
Findings are saved as structured **Markdown Todo files** in the `todos/` directory (e.g., `001-pending-p1-security-sentinel-finding.md`). 

Each file contains:
- Executive Summary & Technical Analysis
- Detailed Findings with Severity (P1/P2/P3) & Category
- Unique Agent Metrics (e.g., Risk Matrix, Typesafety Score)
- Proposed Solutions & Effort Estimates

### Knowledge Base
Key patterns and architectural insights are automatically extracted and codified into the Knowledge Base at the end of every review, ensuring the system gets smarter with every run.

You use the `triage` command to process the pending todos.
