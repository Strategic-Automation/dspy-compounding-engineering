# Knowledge Base

The Knowledge Base is the heart of the **compounding engineering** system. It ensures that every unit of work makes the next one easier by automatically capturing, storing, and reusing learnings.

## Core Concepts

### What Gets Stored?

The KB stores **learnings** - structured insights extracted from:
- Code review findings that were fixed
- Successful todo resolutions
- Triage decisions
- Manual `codify` commands

Each learning contains:
```json
{
  "id": "uuid",
  "timestamp": "2025-12-07T10:00:00Z",
  "source": "work|review|triage|manual",
  "context": "When working on authentication",
  "action": "Use bcrypt for password hashing",
  "rationale": "MD5 is cryptographically broken",
  "tags": ["security", "authentication", "hashing"],
  "category": "best_practice"
}
```

## Storage Architecture

### File Structure

```
.knowledge/
├── learnings/
│   ├── 2025-12-01_security_bcrypt.json
│   ├── 2025-12-02_architecture_factory.json
│   └── ...
├── index.json  # Fast lookup by tags/categories
└── AI.md       # Human-readable consolidated learnings
```

### AI.md

A markdown file auto-generated from all learnings, organized by category. This serves as:
- Human-readable documentation
- Quick reference for developers
- Input for future AI context (if KB retrieval fails)

## Automatic Learning Flow

### 1. Capture (Auto-Codification)

After every `work` command execution:
```python
# In workflows/work_unified.py
learnings = LearningExtractor.extract_from_todo(
    todo_path=completed_todo,
    changes_made=git_diff
)
for learning in learnings:
    kb.save_learning(learning)
```

### 2. Retrieval (Auto-Injection)

Before every AI operation:
```python
# Get relevant past learnings
kb_context = kb.retrieve_relevant(
    query="security review",
    tags=["security"],
    max_results=5
)

# Inject into agent prompt
agent_output = agent.predict(
    code=code_to_review,
    context=kb_context  # Automatically added
)
```

### 3. Evolution (Auto-Gardening)

The `KnowledgeGardener` agent (future enhancement) will:
- Merge duplicate learnings
- Generalize specific patterns
- Archive outdated learnings
- Compress `AI.md` to stay concise

## Retrieval Mechanism

### Hybrid Search (Dense + Sparse)

The system uses **Hybrid Search** by default to provide the best possible relevance. This combines:

1.  **Dense Retrieval (Semantic)**: Uses vector embeddings to find learnings that are semantically similar to your query (e.g., "auth" matches "login").
2.  **Sparse Retrieval (Keyword)**: Uses BM25-style keyword matching to find exact term overlaps (e.g., "SQLi" matches "SQLi").

Results are combined using **Reciprocal Rank Fusion (RRF)** to ensure high-quality context injection.

### Supported Embedding Models

The system is flexible and supports multiple embedding providers:

-   **OpenAI**: `text-embedding-3-small` (default), `text-embedding-3-large`, `text-embedding-ada-002`.
-   **Local (FastEmbed)**: `jinaai/jina-embeddings-v2-small-en` (fallback).
-   **Local (Ollama/Mxbai)**: `mxbai-embed-large:latest` (1024 dimensions).
-   **Nomic/MiniLM**: `nomic-embed-text`, `all-MiniLM-L6-v2`, etc.

### Fallback: Keyword Matching

If a Vector Database (Qdrant) is not available, the system automatically falls back to:

```python
def retrieve_relevant(self, query: str, tags: list = None, max_results: int = 5):
    # 1. Load all learnings from .knowledge/learnings/
    # 2. Score each by keyword overlap with query
    # 3. Filter by tags if provided
    # 4. Return top N by score
```

While functional, keyword fallback lacks semantic understanding and is less effective at finding related but differently-worded patterns.

## Usage Examples

### Manual Codification

```bash
# After a meeting decision
uv run python cli.py codify "All database migrations must have rollback scripts" --source retro

# After fixing a subtle bug
uv run python cli.py codify "When using asyncio, always await database connections"
```

### Automatic Codification

Happens automatically during `work`:
1. Agent fixes a todo (e.g., "Fix SQL injection in login")
2. `LearningExtractor` analyzes the fix
3. Extracts: "Always use parameterized queries, not string concatenation"
4. Saves to KB with tags: `["security", "database", "sql"]`

### KB-Augmented Review

```python
# In workflows/review.py
for agent in review_agents:
    # KB automatically injects past learnings
    findings = agent.review(
        code=diff,
        # No manual context needed - KBPredict wrapper handles it
    )
```

## Knowledge Categories

| Category | Description | Example |
|----------|-------------|---------|
| `best_practice` | Coding standards | "Use type hints in Python 3.10+" |
| `pattern` | Architecture patterns | "Use Factory for agent creation" |
| `gotcha` | Known pitfalls | "os.chdir() is not thread-safe" |
| `security` | Security rules | "Never log passwords" |
| `performance` | Optimization tips | "Cache API responses for 5min" |
| `decision` | ADRs | "Use PostgreSQL not MySQL" |

## Viewing Your Knowledge

### Command Line
```bash
# View AI.md summary
cat .knowledge/AI.md

# Search learnings
grep -r "authentication" .knowledge/learnings/
```

### Programmatically
```python
from utils.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
learnings = kb.retrieve_relevant("authentication", tags=["security"])
for l in learnings:
    print(f"{l['action']} - {l['rationale']}")
```

## Maintenance

### Pruning Old Learnings

Currently manual:
```bash
# Remove outdated learnings
rm .knowledge/learnings/2024-01-*
# Regenerate AI.md
uv run python cli.py codify "trigger regeneration" --source manual
```

Future: Automatic archiving of learnings older than 6 months (configurable).

## Integration with DSPy

The `KBPredict` wrapper extends DSPy's `Predict`:
```python
class KBPredict(dspy.Predict):
    def forward(self, **kwargs):
        # 1. Generate query from kwargs
        query = self._create_kb_query(kwargs)
        # 2. Retrieve learnings
        learnings = kb.retrieve_relevant(query)
        # 3. Inject as 'context' field
        kwargs['context'] = format_learnings(learnings)
        # 4. Call parent Predict
        return super().forward(**kwargs)
```

This means **every agent automatically benefits from past learnings** without workflow changes.

## Metrics (Future)

Track the compounding effect:
- **Learnings Captured**: Total count over time
- **Reuse Rate**: How often learnings are injected
- **Pattern Frequency**: Most commonly reused patterns
- **Time Saved**: Estimated time saved by auto-applying past solutions
