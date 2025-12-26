# Smart Context Gathering

Compounding Engineering uses an intelligent context gathering system to ensure that agents have exactly the information they need, without overwhelming the LLM's context window or wasting tokens.

## The Problem

Naive context gathering (concatenating all files in a repository) suffers from two major issues:
1.  **Token Bloat**: Including irrelevant files (like lock files, large assets, or distant modules) quickly exhausts context windows.
2.  **Noise**: Providing too much irrelevant context can distract the LLM, leading to lower quality reasoning and hallucinations.

## The Solution: Smart Context

Our `ProjectContext` service employs a sophisticated multi-pass approach to gathering context:

### 1. Relevance Scoring (`RelevanceScorer`)

We use a heuristic and semantic scoring engine to weight files based on:
-   **Critical Files**: Files like `pyproject.toml`, `package.json`, and `README.md` are always included.
-   **Path Matching**: Filenames and paths that match keywords in the user's task description receive a significant boost.
-   **Heuristics**: Source code and configuration files are prioritized over documentation or ancillary assets.

### 2. Token Budgeting

The system strictly enforces a token budget:
-   **Window Limit**: We default to a safe 128k limit (configurable).
-   **Reserve**: We reserve space for the agent's output.
-   **Tiered Loading**: We load files in order of their relevance score until the budget is exhausted.

### 3. PII & Secret Scrubbing

To follow our **Local-First** security philosophy, all content is passed through a `SecretScrubber` before being sent to the LLM. This redacts:
-   API Keys and Secrets
-   Personally Identifiable Information (PII)
-   Sensitive environment variables

## Implementation Details

-   **Scoring Logic**: Found in `utils/context/scorer.py`.
-   **Context Orchestration**: Managed by `utils/context/project.py`.
-   **Budget Management**: Uses `utils/token/counter.py` for accurate estimation.

## Configuration

You can tune the context system in your `.env` file:

```bash
# Set the maximum tokens allowed for input context
CONTEXT_WINDOW_LIMIT=128000

# Reserved tokens for the model's response
CONTEXT_OUTPUT_RESERVE=4096
```
