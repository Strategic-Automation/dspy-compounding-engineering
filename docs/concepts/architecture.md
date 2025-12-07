# Architecture

The Compounding Engineering system follows a layered architecture designed to maximize modularity, testability, and the **compounding effect** of accumulated knowledge.

## System Layers

```mermaid
graph TB
    CLI[CLI Layer<br/>cli.py] --> Workflows[Orchestration Layer<br/>workflows/]
    Workflows --> Agents[Intelligence Layer<br/>agents/]
    Workflows --> KB[Knowledge Layer<br/>utils/knowledge_base.py]
    Agents --> KB
    Agents --> DSPy[DSPy Framework]
    KB --> Storage[.knowledge/ JSON Files]
    Workflows --> Utils[Infrastructure Layer<br/>utils/]
    
    style KB fill:#4CAF50,stroke:#333,stroke-width:2px
    style CLI fill:#2196F3,stroke:#333,stroke-width:2px
    style Agents fill:#9C27B0,stroke:#333,stroke-width:2px
```

## 1. CLI Layer

**Purpose**: User-facing interface.

**Implementation**: `cli.py` using the `typer` library.

**Commands**:
- `review`: Multi-agent code review
- `triage`: Interactive findings management
- `work`: Unified todo/plan execution
- `plan`: Feature planning
- `codify`: Explicit learning capture

## 2. Orchestration Layer (Workflows)

**Purpose**: Complex multi-step process coordination.

**Location**: `workflows/`

**Key Workflows**:
- **`review.py`**: Parallelizes 10+ review agents, collects findings, creates todos
- **`triage.py`**: Interactive UI for approving/rejecting findings
- **`work_unified.py`**: ReAct-based execution engine with parallel support
- **`plan.py`**: Repository research and plan generation
- **`codify.py`**: Manual knowledge injection

**Responsibilities**:
- State management (files, branches, worktrees)
- User interaction (prompts, progress bars)
- Agent coordination
- Error handling and retry logic

## 3. Intelligence Layer (Agents)

**Purpose**: AI-powered task execution using DSPy.

**Location**: `agents/`

**Structure**:
- `workflow/`: Task execution agents (ReAct, Planning, Editing)
- `review/`: Specialized review agents (Security, Performance, etc.)
- `research/`: Repository analysis agents

**DSPy Integration**:
- **Signatures**: Define input/output contracts (e.g., `GeneratePlan`, `ReviewCode`)
- **Modules**: Chain multiple signatures with reasoning
- **KBPredict Wrapper**: Automatically injects Knowledge Base context

## 4. Knowledge Layer

**Purpose**: The compounding engine.

**Components**:
- **Storage**: `.knowledge/` directory with JSON files
- **Retrieval**: `KnowledgeBase.retrieve_relevant()` for keyword/tag matching
- **Injection**: `KBPredict` wrapper that augments all agent calls
- **Codification**: `LearningExtractor` automatically captures patterns from work sessions

**Auto-Injection Flow**:
```mermaid
sequenceDiagram
    participant W as Workflow
    participant KB as KnowledgeBase
    participant Agent as DSPy Agent
    
    W->>KB: retrieve_relevant("security review")
    KB-->>W: [Past security learnings]
    W->>Agent: predict(code, context=learnings)
    Agent-->>W: Review output
    W->>KB: save_learning(new_pattern)
```

## 5. Infrastructure Layer (Utils)

**Purpose**: Cross-cutting concerns.

**Components**:
- **`git_service.py`**: Git operations, worktree management
- **`project_context.py`**: Codebase file gathering
- **`todo_service.py`**: Todo file CRUD
- **`file_tools.py`**: Safe file I/O with backups
- **`kb_module.py`**: DSPy integration for KB

## Key Design Patterns

### 1. ReAct Loop (Reasoning + Acting)
Agents follow a **Think → Act → Observe** cycle:
- **Think**: Generate reasoning about what to do next
- **Act**: Use a tool (search, read, edit)
- **Observe**: Process the result and decide next step

### 2. KB Auto-Injection
Every DSPy prediction automatically receives relevant context from past learnings:
```python
# In workflows/work_unified.py
kb_context = kb.retrieve_relevant(query=f"todo resolution: {task_description}")
result = agent.predict(task=task, context=kb_context)
```

### 3. Worktree Isolation
For safe parallel execution:
```python
worktree_path = f"worktrees/{branch_name}"
GitService.create_feature_worktree(branch_name, worktree_path)
# Execute work in worktree
# Merge or discard based on result
```

## Data Flow Example: Full Review Cycle

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Review
    participant Agents
    participant KB
    participant Triage
    participant Work
    
    User->>CLI: cli.py review
    CLI->>Review: run_review()
    Review->>KB: Get past learnings
    Review->>Agents: Run 10+ agents in parallel
    Agents-->>Review: Findings
    Review->>Review: Create *-pending-*.md files
    
    User->>CLI: cli.py triage
    CLI->>Triage: run_triage()
    Triage->>User: Interactive approve/reject
    User-->>Triage: Approve findings
    Triage->>Triage: Convert to *-ready-*.md
    
    User->>CLI: cli.py work p1
    CLI->>Work: run_unified_work()
    Work->>KB: Get relevant patterns
    Work->>Work: ReAct loop (edit files)
    Work->>KB: Save new learnings
    Work->>Work: Mark *-complete-*.md
```

## Scalability Considerations

- **Parallel Execution**: Uses `ThreadPoolExecutor` for multi-agent and multi-todo parallelism
- **Context Window Management**: `ProjectContext` truncates files to avoid token limits (future: semantic filtering)
- **Worktree Cleanup**: Automatic cleanup after work completion

## Future Enhancements

- **MCP Integration**: Replace hardcoded tools with Model Context Protocol servers
- **Vector Search**: Upgrade KB retrieval from keyword to semantic similarity
- **Streaming**: Real-time output during long-running agent tasks
