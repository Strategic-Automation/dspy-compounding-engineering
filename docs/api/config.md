# Configuration & CLI API Reference

Auto-generated from docstrings. Do not edit manually.

---

## `config`

Configuration module for Compounding Engineering.

Handles:
- Environment variable loading (.env files)
- DSPy LM configuration with auto-detected max_tokens
- Service registry for Qdrant and API key status
- Project root and hash utilities

### `get_project_root()`

Determine the root directory of the current project.

The function attempts to locate the Git repository root.
If Git metadata is unavailable, it falls back to the current
working directory.

Returns:
    Path: Absolute path to the project root directory.

### `get_project_hash()`

Generate a stable hash for the current project based on its root path.

### `resolve_embedding_config()`

Determine embedding provider, model, and base URL from centralized settings.

### ServiceRegistry

Registry for runtime service status. Singleton pattern.

#### Methods

- `status()`
- `update_status(key, value)` -- Update a status flag safely.
- `reset()` -- Reset all status flags for testing.
- `check_qdrant(force)` -- Check if Qdrant is available. Cached by default.
- `get_qdrant_client()` -- Returns a Qdrant client if available, or None.
- `check_api_keys(force)` -- Check if required API keys are available. Cached by default.
- `get_kb(force)` -- Get or initialize the KnowledgeBase instance.

### AppConfig

Unified configuration for Compounding Engineering.

#### Methods

- `load()` -- Load settings from environment variables.
- `get_vector_size(model_name)` -- Detect vector size for a given model name with heuristics.

### `load_configuration(env_file)`

Load environment variables from multiple sources in priority order.

### `get_model_max_tokens(model_name, provider)`

Auto-detect max output tokens for a model.

Detection order:
1. Litellm model registry
2. OpenRouter API (for openrouter provider)
3. DSPY_MAX_TOKENS env var fallback

### `configure_dspy(env_file)`

Configure DSPy with the appropriate LM provider and settings.


---

## `cli`

No module documentation available.

### `main(env_file)`

Compounding Engineering (DSPy Edition)

### `triage()`

Triage and categorize findings for the CLI todo system.

### `sync(dry_run, pattern)`

Sync todos to GitHub issues.

This command parses todos/*.md files with 'pending' or 'ready' status and:
- Creates new GitHub issues for todos without a github_issue link
- Updates existing issues when todo content has changed
- Writes the GitHub issue URL back into the todo frontmatter

Examples:
    compounding sync                  # Sync all pending/ready todos
    compounding sync --dry-run        # Preview what would be created
    compounding sync -p "*-p1-*"      # Only sync P1 priority todos

### `plan(description)`

Transform feature descriptions or GitHub issues into project plans.

Examples:
    compounding plan "Add user authentication"
    compounding plan 30
    compounding plan https://github.com/user/repo/issues/30

### `work(pattern, dry_run, sequential, max_workers, in_place)`

Unified work command using DSPy ReAct.

Automatically detects input type:
- Todo ID: "001"
- Plan file: "plans/feature.md"
- Pattern: "p1", "security"

**Migration Note**: This command replaces the old `resolve-todo` command.
All todo resolution and plan execution now go through this unified interface.

### `review(pr_url_or_id, project, agent)`

Perform exhaustive multi-agent code reviews.

Args:
    pr_url_or_id: The target to review. Can be:
        - A PR ID (e.g., 86)
        - A full URL (e.g., https://github.com/user/project/pull/86)
        - A branch name (e.g., dev)
        - 'latest' (the default) to review unstaged/local changes

Examples:
    compounding review              # Review local changes
    compounding review 86           # Review PR #86
    compounding review dev          # Review differences against dev
    compounding review --project    # Review entire project
    compounding review -a Security  # Run only security agent

### `generate_agent(description, dry_run)`

Generate a new Review Agent from a natural language description.

This meta-command creates new review agents for the multi-agent review system.
It analyzes the description, designs an appropriate scanning protocol,
and generates the agent code in agents/review/.

Examples:
    compounding generate-agent "Check for SQL injection vulnerabilities"
    compounding generate-agent "Ensure all Python functions have docstrings"
    compounding generate-agent --dry-run "Audit for frontend race conditions"

### `codify(feedback, source)`

Codify feedback into the knowledge base.

This command uses the FeedbackCodifier agent to transform raw feedback
into structured improvements (documentation, rules, patterns) and saves
them to the persistent knowledge base.

Examples:
    compounding codify "Always use strict typing in Python files"
    compounding codify "We should use factory pattern for creating agents" --source retro

### `compress_kb(ratio, dry_run)`

Compress the AI knowledge base (AI.md) using LLM.

This command semantically compresses the knowledge base to reduce token usage
while preserving key learnings and structure.

### `garden(dry_run, deep)`

Tend to the Knowledge Base: Score, Extract, Tier, and Deduplicate.

### `index(root_dir, recreate)`

Index the codebase for semantic search using Vector Embeddings.
Use this to enable agents to find relevant code snippets.
Performs smart incremental indexing (skips unchanged files).

### `status()`

Check the current status of external services (Qdrant, API keys).


---

