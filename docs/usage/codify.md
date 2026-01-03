# Codify Learnings

The `codify` command is the mechanism for explicitly teaching the system. While the system learns automatically from `work` sessions, `codify` allows you to inject specific rules, architectural decisions, or preferences directly into the Knowledge Base.

## Usage

```bash
compounding codify "YOUR FEEDBACK HERE" [OPTIONS]
```

### Arguments

-   `FEEDBACK`: A string containing the rule, pattern, or lesson you want the system to learn.

### Options

-   `--source` / `-s`: Tag the source of this learning. Common tags:
    -   `manual`: Direct input (default)
    -   `pull_request`: From a PR comment
    -   `retro`: From a retrospective meeting
    -   `incident`: From a post-incident review

## Examples

### 1. Architectural Rules

```bash
compounding codify "All API responses must be wrapped in a standard Envelope object"
```

*Future Effect*: Agents will verify this in `review` and implement it in `work`.

### 2. Contextual Preferences

```bash
compounding codify "Use snake_case for Python variables but camelCase for JSON keys"
```

### 3. Deprecations

```bash
compounding codify "Do not use the 'requests' library; use 'httpx' for all async calls"
```

## How It Works

1.  **Analysis**: The `FeedbackCodifier` agent analyzes your natural language input.
2.  **Structuring**: It converts it into a structured **Learning** object:
    -   **Context**: When does this apply? (e.g., "Python files", "API Layer").
    -   **Action**: What should be done? (e.g., "Use httpx").
    -   **Rationale**: Why? (Inferred from input or added by agent).
3.  **Storage**: Saves the JSON learning to `.knowledge/`.
4.  **Indexing**: Updates `AI.md` (human-readable summary) and internal indexes.

## Best Practices

-   **Be Specific**: "Make code better" is hard to enforce. "Limit functions to 50 lines" is enforceable.
-   **Include "Why"**: The system understands rationale. "Use X because Y" is more powerful than just "Use X".
