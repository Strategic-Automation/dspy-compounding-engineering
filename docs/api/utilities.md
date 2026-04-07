# Utilities API Reference

Auto-generated from docstrings. Do not edit manually.

---

## `utils.security.scrubber`

Secret Scrubber module for Compounding Engineering.

This module provides functionality to redact sensitive information like API keys,
passwords, and PII from text before it's sent to an LLM.

### SecretScrubber

Redacts secrets and PII from text using regex patterns.

#### Methods

- `scrub(text)` -- Scrub secrets and PII from the given text.


---

## `utils.todo`

No module documentation available.


---

## `utils.todo.service`

Todo file service for managing the file-based todo tracking system.

This module provides functions for creating, updating, and managing todo files
in the todos/ directory following the compounding engineering workflow.

### `get_next_issue_id(todos_dir)`

Get the next available issue ID by scanning existing todos.

### `sanitize_description(description)`

Convert a description to kebab-case for filename.

### `create_finding_todo(finding, todos_dir, issue_id)`

Create a pending todo file from a review finding.

Args:
    finding: Dict with keys: agent, review, severity (p1/p2/p3),
             category, location, description, solution, effort
    todos_dir: Directory to store todos
    issue_id: Optional specific issue ID, otherwise auto-generated

Returns:
    Path to the created todo file

### `parse_todo(file_path)`

Parse a todo file and return its frontmatter and body.

Args:
    file_path: Path to the todo file

Returns:
    Dict containing 'frontmatter' (dict) and 'body' (str)

### `serialize_todo(frontmatter_dict, body)`

Serialize frontmatter and body back into a string.

Args:
    frontmatter_dict: Dictionary of YAML frontmatter
    body: Content body

Returns:
    String representation of the file

### `atomic_update_todo(file_path, update_fn)`

Atomically update a todo file using a file lock.

Args:
    file_path: Path to the todo file
    update_fn: Function that takes (frontmatter, body) and returns (new_frontmatter, new_body)

Returns:
    True if successful, False otherwise

### `add_work_log_entry(content, action)`

Add a work log entry to the todo content.

Args:
    content: Existing markdown content
    action: Description of the action taken

Returns:
    Updated content with new work log entry

### `get_ready_todos(todos_dir, pattern)`

Find all ready todos in the todos directory, optionally filtered by pattern.

Args:
    todos_dir: Directory containing todos
    pattern: Optional regex pattern to filter filenames

Returns:
    List of absolute file paths

### `complete_todo(file_path, resolution_summary, action_msg, new_status, rename_to_complete)`

Mark a todo as complete, update its content, and optionally rename it.

Args:
    file_path: Path to the todo file
    resolution_summary: Summary of what was done
    action_msg: Short action message for the log
    new_status: New status string (default: "completed")
    rename_to_complete: If True, rename file from *-ready-* or *-pending-* to *-complete-*

Returns:
    Path to the (possibly new) todo file

### `analyze_dependencies(todos)`

Analyze dependencies between todos and create execution plan.

Args:
    todos: List of todo dictionaries with 'id' and 'frontmatter'

Returns:
    Dict containing execution_order (batches) and mermaid_diagram


---

## `utils.mcp`

No module documentation available.


---

## `utils.mcp.client`

No module documentation available.

### MCPManager

Manages connections to MCP servers via stdio and provides synchronous
wrappers around the tools so they can be consumed by DSPy agents.

Since DSPy expects synchronous tools, we run an asyncio event loop
in a background thread to handle the async MCP client operations.

#### Methods

- `connect_all()` -- Discovers and connects to all configured MCP servers.
- `get_tool(tool_name)` -- Retrieves a DSPy Tool wrapper for a given MCP tool name across all servers.
- `get_all_tools()` -- Returns all discovered tools wrapped as DSPy tools.
- `close()` -- Closes all connections.


---

## `utils.context`

No module documentation available.


---

## `utils.context.project`

Project Context Service

This module provides functionality to gather context about the project,
including reading key files (README, pyproject.toml) and gathering source code
for analysis.

### ProjectContext

Helper service for gathering project context and files.

#### Methods

- `get_context()` -- Get basic project context by reading key files.
- `gather_smart_context(task, max_file_size, budget)` -- Gather project files intelligently based on task relevance and token budget.


---

## `utils.context.scorer`

Relevance Scorer module.

This module calculates relevance scores for files based on a task description.
It utilizes tiered logic:
1. Tier 1: Config/Critical files (Always relevant)
2. Tier 2: Content/Semantic match
3. Tier 3: General code

### RelevanceScorer

Scores files based on relevance to a task.

#### Methods

- `score(filepath, content, task, is_test_related)` -- Legacy full-score method.
- `score_path(filepath, task, is_test_related)` -- Score based only on file path and task description.


---

## `utils.search`

No module documentation available.


---

## `utils.search.ddg_search`

DuckDuckGo search implementation for research agents.

### `search_web(query, max_results)`

Search the web using DuckDuckGo.

Args:
    query: The search query string
    max_results: Maximum number of results to return (default: settings.web_search_limit)

Returns:
    List of search results, each containing:
    - title: Page title
    - url: Page URL
    - source: Data source identifier (always 'DuckDuckGo')

### `format_search_results(results)`

Format structured search results into a markdown string for LLM consumption.

### `internet_search(query, max_results)`

Consolidated function for searching the internet and returning formatted markdown.
This is the primary entry point for agent tools.


---

## `utils.knowledge`

No module documentation available.


---

## `utils.knowledge.compression`

No module documentation available.

### CompressMarkdown

Compress the given markdown content while preserving its structure, key details,
and technical accuracy.
Reduce the length by approximately the target ratio (e.g., 0.5 means 50% size).
Retain all headers, code blocks, and list structures where possible.

### LLMKBCompressor

No documentation available.

#### Methods

- `forward(content, ratio)` -- Compresses the given markdown content with caching.


---

## `utils.knowledge.core`

Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.

### KnowledgeBase

Manages a collection of learnings stored in a local SQLite database and indexed in Qdrant.

#### Methods

- `get_codify_lock_path()` -- Returns the path to the codify-specific lock file.
- `get_lock(lock_type)` -- Returns a FileLock instance for the specified type ('kb' or 'codify').
- `save_learning(learning, silent, update_docs)` -- Add a new learning item to the knowledge base (SQLite + Qdrant).
- `retrieve_relevant(query, tags, limit)` -- Search for relevant learnings using Hybrid Search (Qdrant) with Local SQLite fallback.
- `search_local(query, tags, limit)` -- Local search using SQLite LIKE queries.
- `get_all_learnings()` -- Retrieve all learnings from SQLite.
- `get_context_string(query, tags)` -- Get a formatted string of relevant learnings for context injection.
- `get_compounding_ai_prompt(limit)` -- Get a formatted prompt suffix for auto-injection into ALL AI interactions.
- `search_similar_patterns(description, threshold, limit)` -- Search for similar patterns using vector embeddings.
- `index_codebase(root_dir, force_recreate)` -- Delegate to CodebaseIndexer.
- `search_codebase(query, limit)` -- Delegate to CodebaseIndexer.
- `compress_ai_md(ratio, dry_run)` -- Compress the AI.md knowledge base.


---

## `utils.knowledge.docs`

Knowledge Documentation Service.

This module handles the generation, maintenance, and compression of the
AI.md auto-generated documentation file.

### KnowledgeDocumentation

Manages the AI.md documentation file, including generation and compression.

#### Methods

- `get_ai_md_size()` -- Get current size of AI.md in characters.
- `update_ai_md(learnings, silent)` -- Regenerate AI.md from the provided list of learnings.
- `compress_ai_md(ratio, dry_run, silent)` -- Compress AI.md using LLM-based semantic compression.
- `review_and_compress(silent)` -- Auto-review AI.md quality and compress if needed.


---

## `utils.knowledge.embeddings`

No module documentation available.

### EmbeddingProvider

Manages embedding generation using OpenAI-compatible APIs or local FastEmbed.
Implements thread-safe model caching to prevent redundant loads in parallel agents.

#### Methods

- `get_embedding(text)` -- Generate embedding for text using configured provider.
- `get_sparse_embedding(text)` -- Generate sparse embedding for text using fastembed.


---

## `utils.knowledge.extractor`

Learning Extraction Helper Module

Provides reusable functions for extracting and codifying learnings
across all workflows (review, triage, work).

### `codify_learning(context, source, category, metadata, silent)`

Extract and codify learnings from any workflow stage.

Args:
    context: The content to analyze for learnings
    source: Source of the learning (e.g., "review", "triage", "work")
    category: Category for the learning (e.g., "code-review", "triage", "work")
    metadata: Optional metadata to attach to the learning
    silent: If True, don't print status messages

Returns:
    True if learning was successfully codified, False otherwise

### `codify_review_findings(findings, todos_created, silent)`

Extract learnings from code review findings.

This captures code patterns, architectural insights, and best practices
identified during the review process.

Args:
    findings: List of findings from review agents
    todos_created: Number of todos created from the review
    silent: If True, suppress verbose output messages

### `codify_triage_decision(finding_content, decision, reason, proposed_solution)`

Extract learnings from a triage decision.

Args:
    finding_content: The content that was triaged
    decision: The decision made (approved, rejected, completed, etc.)
    reason: Reason for the decision
    proposed_solution: Proposed solution if available

### `codify_work_outcome(todo_id, todo_slug, resolution_summary, operations_count, success)`

Extract learnings from a work resolution outcome.

Args:
    todo_id: ID of the resolved todo
    todo_slug: Slug/description of the todo
    resolution_summary: Summary of how it was resolved
    operations_count: Number of operations performed
    success: Whether resolution was successful

### `codify_batch_triage_session(approved_count, skipped_count, total_count, approved_todos)`

Extract learnings from an entire triage session.

Args:
    approved_count: Number of items approved
    skipped_count: Number of items skipped
    total_count: Total items triaged
    approved_todos: List of approved todo filenames


---

## `utils.knowledge.gardener`

Knowledge Gardening Service.

This module implements the core logic for the "Intelligent Knowledge Gardening" system.
It handles:
1. Scoring: Calculating importance scores for learning items.
2. Extraction: Extracting structured facts from raw learnings.
3. Compression: Tiered compression (Detailed, Compressed, Principle).
4. Deduplication: semantic deduplication using vector embeddings.

### FactStatement

Extract a structured fact statement from a learning item.

### KnowledgeGardener

No documentation available.

#### Methods

- `extract_fact(content)`

### KnowledgeGardeningService

Service to maintain the health and density of the Knowledge Base.

#### Methods

- `garden(dry_run, deep_mode, max_workers)` -- Hybrid Gardening Loop:


---

## `utils.knowledge.indexer`

Codebase Indexer module for Compounding Engineering.

This module manages the indexing of the codebase into Qdrant for semantic search.
It handles file crawling, chunking, embedding generation, and incremental updates.

### CodebaseIndexer

Manages indexing of the codebase using vector embeddings.

#### Methods

- `index_codebase(root_dir, force_recreate)` -- Index the codebase using vector embeddings.
- `search_codebase(query, limit)` -- Search for relevant code snippets.


---

## `utils.knowledge.module`

Knowledge Base Augmented DSPy Module

This module provides a DSPy Module that automatically injects knowledge base
context into LLM calls, enabling true compounding engineering where past
learnings inform future operations.

Based on DSPy best practices: instead of extending dspy.Predict, we create
a custom dspy.Module that wraps it and injects KB context in the forward method.

### KBPredict

DSPy Module that wraps dspy.Predict with automatic KB injection.
Simplified: all logic inlined, dropped base class and unused CoT.

#### Methods

- `wrap(cls, module, kb_tags)` -- Factory method to wrap an existing module with KB augmented context.
- `forward()`


---

## `utils.knowledge.utils`

Shared utilities for vector database collection management.

### CollectionManagerMixin

Mixin to provide shared collection management logic for vector base classes.


---

## `utils.git`

No module documentation available.


---

## `utils.git.service`

No module documentation available.

### GitService

Helper service for Git and GitHub CLI operations.

#### Methods

- `filter_diff(diff_text)` -- Filter out ignored files from a git diff.
- `is_git_repo()` -- Check if current directory is a git repo.
- `get_diff(target)` -- Get git diff for a target (commit, branch, staged, or file path).
- `get_file_status_summary(target)` -- Get a summary of file statuses (Added, Modified, Deleted, Renamed).
- `get_git_log_search(query, path)` -- Deep git log analysis: Search for a string in commit history (git log -S).
- `get_git_blame(file_path)` -- Get git blame for a file to see who last modified each line and when.
- `get_pr_diff(pr_id_or_url)` -- Fetch PR diff using gh CLI.
- `get_pr_details(pr_id_or_url)` -- Fetch PR details (title, body, author) using gh CLI.
- `get_issue_details(issue_id_or_url)` -- Fetch issue details (title, body) using gh CLI.
- `get_current_branch()` -- Get current branch name.
- `get_pr_branch(pr_id_or_url)` -- Get the branch name for a PR using gh CLI.
- `checkout_pr_worktree(pr_id_or_url, worktree_path)` -- Checkout a PR into a worktree.
- `create_feature_worktree(branch_name, worktree_path)` -- Create a worktree for a feature branch (creating branch if needed).


---

## `utils.github`

GitHub utilities package.


---

## `utils.github.service`

GitHub service for issue CRUD operations via gh CLI.

### GitHubService

Service for GitHub issue operations using gh CLI.

#### Methods

- `create_issue(title, body, labels)` -- Create a new GitHub issue.
- `update_issue(issue_number, body, title, add_labels, remove_labels)` -- Update an existing GitHub issue.
- `get_issue(issue_number)` -- Get details of a GitHub issue.
- `list_labels()` -- List all available labels in the repository.
- `issue_exists(issue_number)` -- Check if an issue exists and is accessible.


---

## `utils.agent.tools`

Centralized tool factory for DSPy agents.

This module provides reusable tools for research agents and workflow agents,
ensuring consistent codebase exploration capabilities across the system.

### `get_documentation_tool()`

Returns a tool for fetching external documentation from URLs.

### `get_search_learnings_tool()`

Returns a tool for retrieving codified best practices from the knowledge base.

### `get_internet_search_tool()`

Returns a tool for searching the live internet for current information.

### `get_codebase_search_tool(base_dir)`

Returns a tool for searching strings/patterns in project files.

### `get_semantic_search_tool()`

Returns a tool for semantic/vector search over the indexed codebase.

### `get_file_reader_tool(base_dir)`

Returns a tool for reading specific lines from a file.

### `get_directory_tool(base_dir)`

Returns a tool for listing directory contents.

### `get_git_log_search_tool()`

Returns a tool for searching the repository's git commit history.

### `get_git_blame_tool()`

Returns a tool for running git blame on a file.

### `get_gather_context_tool()`

Returns a tool for gathering smart project context.

### `get_research_tools(base_dir)`

Get the standard set of tools for research agents.
Includes: documentation fetcher, semantic search, codebase grep, file reader.

### `get_work_tools(base_dir)`

Get the standard set of tools for work/execution agents.
Includes: codebase search, semantic search, file reader, directory listing.

### `get_file_editor_tool(base_dir)`

Returns a tool for editing specific lines in a file.

### `get_file_creator_tool(base_dir)`

Returns a tool for creating new files.

### `get_system_status_tool()`

Returns a tool for checking system status.

### `get_audit_logs_tool()`

Returns a tool for reading the system's audit logs.

### `get_todo_resolver_tools(base_dir)`

Get the full set of tools for todo resolution agents.
Includes: directory listing, codebase search, semantic search, file reader,
file editor, file creator, gather context, system status, and audit logs.


---

## `utils.token`

Token Utilities.


---

## `utils.token.counter`

Token Counter module.

This module handles token counting logic using tiktoken,
with caching to improve performance on large codebases.

### TokenCounter

Handles token counting with caching.

#### Methods

- `count_tokens(text, model)` -- Count tokens in text string.


---

## `utils.io`

No module documentation available.


---

## `utils.io.files`

No module documentation available.

### `list_directory(path, base_dir)`

List files and directories at the given path.
Returns a formatted string listing contents.

### `search_files(query, path, regex, base_dir, limit)`

Search for a string or regex in files at the given path.
Uses git grep if available, otherwise falls back to grep -r with exclusions.

### `read_file_range(file_path, start_line, end_line, base_dir)`

Read a file within a specific line range (1-based).
If end_line is -1, read to the end.

### `edit_file_lines(file_path, edits, base_dir)`

Edit specific lines in a file.

Args:
    file_path: Path to the file (relative to base_dir)
    edits: List of dicts with keys:
    - start_line: int (1-indexed)
    - end_line: int (1-indexed, inclusive)
    - content: str (new content)
    base_dir: Base directory for path resolution

Edits must be non-overlapping and sorted by start_line (descending) to avoid index shifts,
but we will handle sorting here.

### `create_file(file_path, content, base_dir)`

Create a new file with the given content.
Fails if file already exists.

### `get_project_context(task, base_dir)`

Gather relevant project context (file contents) based on a task description.
Uses smart relevance scoring and lazy loading.


---

## `utils.io.logger`

No module documentation available.

### InterceptHandler

Redirects standard logging messages to Loguru.

#### Methods

- `emit(record)`

### `configure_logging(log_path)`

Configures Loguru and intercept handlers. Lazily called or via bootstrap.

### SystemLogger

Centralized logger for Compounding Engineering.

Design Philosophy:
- CLI: clean, minimal, user-focused (Success, Warning, Error only).
- File: comprehensive, detailed, developer-focused (Debug, Info, + CLI events).

#### Methods

- `info(msg, to_cli)` -- Log info - writes to FILE. Optionally writes to CLI if to_cli=True.
- `debug(msg)` -- Debug log - writes to FILE ONLY. clean CLI.
- `success(msg)` -- Success log - shows in CLI and writes to file.
- `warning(msg)` -- Warning log - shows in CLI and writes to file.
- `error(msg, detail)` -- Error log - shows in CLI and writes to file.
- `status(msg)` -- Returns a status context for rich spinners.
- `get_logs(limit)` -- Read the last N lines from the log file using a memory-efficient backward seek.


---

## `utils.io.safe`

No module documentation available.

### `validate_path(path, base_dir)`

Validate path is relative and within base_dir, preventing traversal.

### `run_safe_command(cmd, cwd, capture_output, text, check)`

Safely execute a command from an allowlist.
Disallows shell=True and validates the executable.

### `safe_write(file_path, content, base_dir, overwrite)`

Safely write content to file within base_dir.
If overwrite is False and file exists, raises FileExistsError.

### `safe_delete(file_path, base_dir)`

Safely delete file or directory within base_dir.

### `validate_agent_filters(agent_filters)`

Validate and sanitize agent filter terms.

Args:
    agent_filters: List of agent filter strings from CLI

Returns:
    Sanitized list of valid filters, or None if no valid filters remain


---

## `utils.io.status`

No module documentation available.

### `get_system_status()`

Get the current health and status of external services (Qdrant, API keys).
Returns a formatted description of the system status.


---

## `utils.web`

No module documentation available.


---

## `utils.web.documentation`

No module documentation available.

### PinnedTransport

Custom transport that pins a hostname to a specific IP address.
Ensures SNI and Host headers remain correct for SSL/TLS validation.

#### Methods

- `handle_request(request)`

### DocumentationFetcher

Utility for fetching and parsing official documentation from URLs.
Supports high-quality conversion via r.jina.ai and local fallback.

#### Methods

- `fetch(url, max_tokens, offset_tokens)` -- Fetch documentation from a URL and return it as Markdown.


---

