# Compounding Engineering -- Development Guide

Instructions for AI coding assistants and agentic frameworks (Hermes, Codex,
Claude Code, Copilot) working on the dspy-compounding-engineering codebase.

This is a **DSPy-native CLI tool** that implements the Compounding Engineering
philosophy: every unit of work makes subsequent work easier. It provides
multi-agent code review, planning, triage, and automated work execution --
all backed by a self-improving knowledge base.

---

## Project Structure

```
dspy-compounding-engineering/
├── pyproject.toml                 # Dependencies, ruff, pytest, build config
├── AGENTS.md                      # This file -- mandatory for all AI agents
├── cli.py                         # Typer CLI entry point
├── config.py                      # AppConfig + ServiceRegistry + DSPy configuration
├── docker-compose.yml             # Qdrant vector DB
│
├── agents/                        # DSPy agent definitions
│   ├── knowledge_gardener.py
│   ├── schema/
│   │   ├── base.py                # Base Pydantic models
│   │   ├── research.py            # Research input/output schemas
│   │   ├── review.py              # Review finding schemas
│   │   └── workflow.py            # Workflow/todo schemas
│   ├── review/                    # Multi-agent review specialists
│   │   ├── security_sentinel.py
│   │   ├── performance_oracle.py
│   │   ├── architecture_strategist.py
│   │   ├── data_integrity_guardian.py
│   │   ├── code_simplicity_reviewer.py
│   │   ├── agent_native_reviewer.py
│   │   ├── kieran_python_reviewer.py
│   │   ├── pattern_recognition_specialist.py
│   │   └── ...
│   ├── research/                  # Research agents
│   │   ├── repo_research_analyst.py
│   │   ├── best_practices_researcher.py
│   │   ├── framework_docs_researcher.py
│   │   └── git_history_analyzer.py
│   └── workflow/                  # Workflow agents
│       ├── plan_generator.py
│       ├── task_executor.py
│       ├── task_validator.py
│       ├── triage_agent.py
│       ├── command_generator.py
│       ├── feedback_codifier.py
│       └── ...
│
├── workflows/                     # Orchestration layer
│   ├── review.py                  # Multi-agent review pipeline
│   ├── triage.py                  # Interactive finding triage
│   ├── work.py                    # Unified work execution (ReAct)
│   ├── plan.py                    # Feature planning workflow
│   ├── codify.py                  # Knowledge codification
│   ├── sync.py                    # GitHub issue sync
│   └── generate_agent.py          # Meta agent generation
│
├── utils/                         # Infrastructure utilities
│   ├── io/
│   │   ├── files.py               # File I/O with safety guards
│   │   ├── logger.py              # Loguru logging setup
│   │   ├── safe.py                # Safe command execution
│   │   ├── status.py              # System status reporting
│   │   └── __init__.py            # get_system_status(), validate_agent_filters()
│   ├── knowledge/
│   │   ├── core.py                # KnowledgeBase class
│   │   ├── indexer.py             # Codebase indexing (Qdrant + keyword)
│   │   ├── embeddings.py          # Embedding provider abstraction
│   │   ├── gardener.py            # Knowledge gardening service
│   │   ├── extractor.py           # Learning extraction
│   │   ├── compression.py         # AI.md compression
│   │   └── docs.py                # Documentation fetching
│   ├── git/
│   │   └── service.py             # Git operations + worktree management
│   ├── github/
│   │   └── service.py             # GitHub API integration (PyGithub)
│   ├── mcp/
│   │   └── client.py              # MCP client
│   └── context/
│       ├── project.py             # Project context gathering
│       └── scorer.py              # Context relevance scoring
│
├── mcp_servers/                   # MCP server implementations
│   ├── compounding_server.py      # Main FastMCP server
│   ├── file_server.py
│   ├── git_server.py
│   └── search_server.py
│
├── tests/                         # Pytest suite
├── todos/                         # Pending review findings (markdown)
├── plans/                         # Feature implementation plans
├── docs/                          # MkDocs documentation
└── .knowledge/                    # Knowledge base (auto-populated)
```

---

## CORE RULES (VIOLATIONS ARE REJECTED)

### 1. ALWAYS use f-strings
Never use `.format()` or `%s` style string formatting.

```python
f"Reviewing {count} files"           # GOOD
"Reviewing {} files".format(count)   # BAD
```

### 2. ALWAYS use Pydantic BaseModel in DSPy Signatures
Every `dspy.InputField()` and `dspy.OutputField()` carrying structured data
MUST use a typed Pydantic `BaseModel`. Never use raw types (`str`, `float`,
`list[dict]`) in signatures.

```python
class ReviewFinding(BaseModel):
    file: str
    line: int
    severity: str
    description: str
    fix_strategy: str

class ReviewSignature(dspy.Signature):
    code_context: str = dspy.InputField()
    findings: list[ReviewFinding] = dspy.OutputField()
```

### 3. NEVER use `from __future__ import annotations`
Breaks DSPy type introspection and Pydantic forward reference resolution.
If a forward reference is needed, just drop the type annotation — do NOT use
`TYPE_CHECKING` guards.

### 4. NEVER post-process LLM outputs
If the LLM generates invalid output, Pydantic rejects it and DSPy's retry
mechanisms handle it. Post-processing masks root cause prompting issues.

### 5. Fix root causes, not symptoms
Do not add defensive dedup, defensive casting, or workarounds. Fix the
underlying prompt, signature, or logic that caused the issue.

### 6. Use `AppConfig` from `config.py` for configuration
The project uses a plain `AppConfig` class that reads `os.getenv()` directly.
Centralised configuration is in `config.py` — add new env vars there
with defaults and include them in the `load()` method. Do NOT add
`pydantic-settings` or `BaseSettings` unless the team explicitly migrates.

### 7. `TYPE_CHECKING` guards for forward references are acceptable
The knowledge base uses `from typing import TYPE_CHECKING` for Qdrant client
imports. Prefer this pattern when a forward reference would otherwise require
`from __future__ import annotations`.

### 8. All tools MUST return JSON strings
DSPy tool compatibility requires JSON string returns.

```python
def search_codebase(query: str, limit: int = 5) -> str:
    """Search the codebase for relevant files and functions."""
    import json
    results = _do_search(query, limit)
    return json.dumps({"success": True, "results": results, "count": len(results)})
```

### 9. Tools MUST have docstrings and type hints
DSPy reads docstrings and parameter types to build schemas for the LLM.

```python
def fetch_documentation(url: str, max_pages: int = 10) -> str:
    """Fetch and convert documentation pages to markdown using Jina Reader.
    Returns a JSON string of title, content, and source URL for each page."""
```

---

## DSPy MODULE PATTERNS

### Review Agents are Signatures, NOT Modules
Review agents (`agents/review/`) are **pure `dspy.Signature` classes** with
metadata. They contain NO `dspy.Module` subclasses -- they are discovered
dynamically and wrapped with `KBPredict` at runtime.

```python
class SecuritySentinel(dspy.Signature):
    """You are an elite Application Security specialist..."""
    
    __agent_name__: ClassVar[str] = "Security Sentinel"
    __agent_category__: ClassVar[str] = "security"
    __agent_severity__: ClassVar[str] = "p1"
    applicable_languages: ClassVar[Optional[Set[str]]] = None

    code_diff: str = dspy.InputField(desc="The code changes to review")
    review_report: SecurityReport = dspy.OutputField(desc="Structured security audit report")
```

### The `KBPredict` Wrapper is Core
All agent calls go through `KBPredict` which automatically injects past
knowledge base learnings into the LLM context. This is the compounding
mechanism -- the system gets smarter with every use.

```python
# In workflows:
from utils.knowledge import KBPredict

predictor = KBPredict.wrap(
    agent_cls,
    kb_tags=["code-review", "security", "security-sentinel"],
)
result = predictor(code_diff=diff)
```

### Tool-use nodes use ReAct
Nodes that need external tools must use `dspy.ReAct`.

```python
class AgentGeneratorModule(dspy.Module):
    def __init__(self, tools):
        super().__init__()
        self.generator = dspy.ReAct(AgentGeneratorSignature, tools=tools)

    def forward(self, description: str) -> dspy.Prediction:
        return self.generator(description=description)
```

### Analysis nodes use ChainOfThought
Non-tool nodes use `dspy.ChainOfThought`.

```python
class PlanAnalysisModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought(PlanSignature)

    def forward(self, description: str, repo_context: str) -> dspy.Prediction:
        return self.analyzer(description=description, repo_context=repo_context)
```

### No `dspy.Refine` -- Knowledge Base is the Compounding Engine
Unlike other DSPy projects, this project does NOT use `dspy.Refine` for
self-improvement. The "compounding" happens through **knowledge base
auto-injection** via `KBPredict`. Every todo resolution, review finding,
and codification adds learnings that are automatically retrieved and
injected into future agent calls. No manual retry loops needed.

### Temperature Control
```python
# Precision tasks (review, triage): low temperature
with dspy.settings.context(temperature=0.1):
    findings = agent(code_context=diff)

# Planning/generation: slightly higher
with dspy.settings.context(temperature=0.4):
    plan = planner(description=desc)
```

---

## PYDANTIC SCHEMA PATTERNS

### Schema files by domain
Schemas are organised in `agents/schema/`:
- `base.py` — shared base models
- `review.py` — review finding and resolution schemas
- `research.py` — research input/output schemas
- `workflow.py` — workflow, todo, and planning schemas

New schemas go in the appropriate file. Do NOT scatter models across modules.

### Nested Models in OutputFields
```python
class AttackStep(BaseModel):
    step_number: int
    action: str
    tool: str
    expected_outcome: str

class WorkPlan(BaseModel):
    steps: list[AttackStep]
    estimated_effort: str
```

---

## KNOWLEDGE BASE

The compounding engine centres on the knowledge base:

| Feature | Details |
|---------|---------|
| Storage | `.knowledge/` directory (JSON learnings + `AI.md`) |
| Vector search | Qdrant (Docker) with keyword fallback |
| Auto-injection | All AI ops receive relevant past learnings |
| Auto-codification | Every todo resolution extracts learnings |
| Gardening | `garden` command — scoring, dedup, tiering |
| Compression | `compress-kb` command — LLM-based AI.md compression |

Agents should query the knowledge base before making decisions. This is the
core mechanism by which each unit of work compounds over time.

---

## CLI COMMANDS

| Command | Purpose |
|---------|---------|
| `compounding review` | Multi-agent code review |
| `compounding triage` | Interactive finding triage |
| `compounding work <pattern>` | Resolve todos / execute plans via ReAct |
| `compounding plan <description>` | Generate implementation plans |
| `compounding codify <feedback>` | Capture learnings to KB |
| `compounding generate-agent <desc>` | Create new review agents |
| `compounding sync` | Sync todos to GitHub issues |
| `compounding garden` | Knowledge base maintenance |
| `compounding compress-kb` | Compress AI.md |
| `compounding index` | Index codebase for semantic search |
| `compounding status` | Check service diagnostics |

---

## CONFIGURATION

The project uses `AppConfig` in `config.py` which loads from environment
variables and `.env` files in priority order:

1. `--env-file` flag
2. `COMPOUNDING_ENV` environment variable
3. `.env` in project root
4. `~/.config/compounding/.env`
5. `~/.env`

DSPy is configured via `configure_dspy()` which supports OpenAI, Anthropic,
Ollama, and OpenRouter providers.

```bash
DSPY_LM_PROVIDER=openrouter
DSPY_LM_MODEL=anthropic/claude-sonnet-4-5-20250929
OPENROUTER_API_KEY=***
```

Langfuse observability is auto-enabled when both `LANGFUSE_PUBLIC_KEY` and
`LANGFUSE_SECRET_KEY` are present.

---

## TESTING

```bash
cd /media/haylerd/External/repos/StrategicAutomation/dspy-compounding-engineering
source .venv/bin/activate  # If using local venv, or use uv run

pytest tests/ -q                        # Full suite
pytest tests/test_knowledge_base.py -q  # Knowledge base tests
pytest tests/test_mcp.py -q             # MCP integration tests
pytest tests/test_search_limit.py -q    # Search tests
```

### TDD Workflow
1. Write the test first
2. Implement the code
3. Run the tests — MUST pass
4. Only then commit

**Never commit untested code.** After every feature: create a new git branch,
write tests for all new code, run the tests, verify they pass, then commit.

Git branch naming: `issue/{number}-{short-description}`

---

## LINTING & FORMAT

```bash
ruff check agents/ workflows/ utils/ tests/
ruff format agents/ workflows/ utils/ tests/
```

Ruff rules: E, W, F, I, C, B. Line length: 100. Target: Python 3.10+.

---

## MCP SERVER

`compounding-mcp` exposes the CLI workflows as MCP tools:
- `compounding_review`
- `compounding_plan`
- `compounding_work`
- `compounding_triage`
- `compounding_sync`

The MCP server (`mcp_servers/compounding_server.py`) uses FastMCP. Other
servers in `mcp_servers/` provide file, git, and search capabilities.

---

## COMMON PITFALLS

| Pitfall | Fix |
|---------|-----|
| `from __future__ import annotations` | NEVER. Breaks DSPy type introspection. Use `TYPE_CHECKING` for forward refs. |
| Raw types in signatures | ALWAYS use Pydantic BaseModel for OutputFields. |
| `.format()` or `%s` strings | ALWAYS use f-strings. |
| Post-processing agent outputs | NEVER. Fix the root prompt or signature instead. |
| Hardcoding `.knowledge/` paths | Use `settings.knowledge_dir_name` from config. |
| Missing tool docstrings | Tools MUST have docstrings — DSPy reads them for schema generation. |
| Adding new review agents | Must include `__agent_name__`, `__agent_category__`, `__agent_severity__` metadata. |
| Using `dspy.Refine` | Not the compounding pattern here. Use `KBPredict` for KB injection. Compounding comes from knowledge base auto-injection, not self-eval retries. |

---

## CI/CD

GitHub Actions workflows:
- `test.yml` — pytest on push/PR
- `docs.yml` — MkDocs deploy to GitHub Pages
- `publish.yml` — Package publishing
- `branch-enforcement.yml` — Branch naming conventions
- `release-tagging.yml` — Release automation
