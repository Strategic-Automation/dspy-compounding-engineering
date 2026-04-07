# Workflows API Reference

Auto-generated from docstrings. Do not edit manually.

---

## `workflows.codify`

Codify Workflow

This workflow allows users to manually codify feedback, learnings, or instructions
into the persistent knowledge base using the FeedbackCodifier agent.

### `run_codify(feedback, source)`

Codify feedback into the knowledge base.

Args:
    feedback: The raw text to codify.
    source: The source of the feedback (e.g., "manual", "review", "retro").


---

## `workflows.generate_agent`

Generate Agent Workflow

This workflow generates new Review Agents for the Compounding Engineering
based on natural language descriptions.

### `run_generate_agent(description, dry_run)`

Generate a new review agent from a natural language description.

Args:
    description: Description of what the review agent should check for
    dry_run: If True, show what would be created without writing files


---

## `workflows.plan`

No module documentation available.

### `run_plan(feature_description)`

Orchestrate the planning process.


---

## `workflows.review`

No module documentation available.

### `detect_languages(code_content)`

Detect programming languages from file paths in code content.
Returns a set of detected language identifiers.

### `discover_reviewers()`

Dynamically discover all review agents in the agents.review package.
Expects agents to be dspy.Signature classes with:
- __agent_name__: Human-readable name
- __agent_category__: Category (e.g. security)
- __agent_severity__: Priority (p1, p2, p3)
- applicable_languages: Set of languages or None

### `convert_pydantic_to_markdown(model)`

Convert any Pydantic model into a structured markdown report.
Auto-detects findings lists and summary fields.

### `run_review(pr_url_or_id, project, agent_filter)`

Perform exhaustive multi-agent code review.


---

## `workflows.sync`

Sync workflow for creating/updating GitHub issues from todos.

This module parses todos/*.md files and synchronizes them with GitHub issues,
creating new issues for todos without existing links and updating existing ones.

### `run_sync(dry_run, pattern, todos_dir)`

Synchronize todos to GitHub issues.

Args:
    dry_run: If True, preview changes without creating issues
    pattern: Glob pattern to filter todo files
    todos_dir: Directory containing todo files

Returns:
    Dict with 'created', 'updated', 'skipped' counts and lists


---

## `workflows.triage`

No module documentation available.

### `consistency_check_todos(todos_dir)`

No documentation available.

### `validate_references(content, todos_dir)`

Validate that any todo IDs referenced in the content exist.

### `run_triage()`

No documentation available.


---

## `workflows.work`

No module documentation available.

### `run_unified_work(pattern, dry_run, parallel, max_workers, in_place)`

Unified work command using DSPy ReAct for todo resolution and plan execution.


---

