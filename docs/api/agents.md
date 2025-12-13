# Agents API Reference

The system uses specialized DSPy agents for different tasks. Each agent is implemented as a DSPy `Signature` or `Module`.

## Review Agents

Located in `agents/review/`, these agents analyze code for specific concerns.

### SecuritySentinel
**Module**: `agents/review/security_sentinel.py`

Detects security vulnerabilities.

**Checks**:
- SQL injection via string concatenation
- XSS vulnerabilities in web output
- Insecure cryptographic functions (MD5, SHA1)
- Hardcoded secrets/credentials
- Path traversal vulnerabilities
- CORS misconfigurations

**Output**: `SecurityReport` (Pydantic model) containing a list of findings with severity.

### PerformanceOracle
**Module**: `agents/review/performance_oracle.py`

Identifies performance issues.

**Checks**:
- O(n²) or worse algorithmic complexity
- N+1 query problems in ORMs
- Inefficient loops and iterations
- Missing database indexes
- Unoptimized regular expressions
- Memory leaks

### ArchitectureStrategist
**Module**: `agents/review/architecture_strategist.py`

Reviews system design and patterns.

**Checks**:
- SOLID principle violations
- Improper dependency injection
- God objects and tight coupling
- Missing abstraction layers
- Circular dependencies

**Output**: `ArchitectureReport` (Pydantic model) containing analysis and findings.

### DataIntegrityGuardian
**Module**: `agents/review/data_integrity_guardian.py`

Ensures data consistency and validation.

**Checks**:
- Missing input validation
- Transaction boundary issues
- Data race conditions
- Schema migration problems
- Improper error handling in DB operations

### TestCoverageWarden
**Module**: `agents/review/test_coverage_warden.py`

Ensures adequate testing.

**Checks**:
- Missing unit tests for new code
- Untested error paths
- Missing integration tests
- Test quality issues

### MaintainabilitySage
**Module**: `agents/review/maintainability_sage.py`

Reviews code quality and readability.

**Checks**:
- Poor naming conventions
- Excessive function/class complexity
- Missing documentation
- Code duplication
- Magic numbers and hardcoded values

## Workflow Agents

Located in `agents/workflow/`, these agents execute tasks.

### TaskPlanner
**Signature**: `GeneratePlan`

Transforms feature descriptions into structured implementation plans.

**Inputs**:
- `feature_description`: str
- `project_context`: str
- `kb_context`: str (auto-injected)

**Outputs**:
- `plan_markdown`: str (full plan in markdown format)

### TaskExecutor (ReAct Agent)
**Module**: `agents/workflow/task_executor.py`

Executes todos and plans using a ReAct (Reasoning + Acting) loop.

**Tools Available**:
- `search_files`: Grep-like search across codebase
- `read_file`: Read file contents with line ranges
- `edit_file`: Apply line-based edits
- `list_directory`: Show directory contents
- `run_command`: Execute shell commands (optional)

**Process**:
1. **Think**: Reason about what to do next
2. **Act**: Choose and use a tool
3. **Observe**: Process tool output
4. Repeat until task complete

### FeedbackCodifier
**Signature**: `CodifyFeedback`

Converts natural language feedback into structured learnings.

**Inputs**:
- `feedback`: str (user input)
- `source`: str (origin of feedback)

**Outputs**:
- `context`: str (when this applies)
- `action`: str (what to do)
- `rationale`: str (why this matters)
- `tags`: List[str] (categorization)
- `category`: str (best_practice, pattern, gotcha, etc.)

### LearningExtractor
**Module**: `agents/workflow/learning_extractor.py`

Automatically extracts patterns from completed work.

**Inputs**:
- `todo_path`: str
- `git_diff`: str
- `test_results`: Optional[str]

**Outputs**:
- List of structured learnings

## Research Agents

Located in `agents/research/`, these agents gather context.

### RepositoryExplorer
Analyzes codebase structure and patterns.

### FrameworkDetector
Identifies frameworks and libraries in use.

### PatternMatcher
Finds existing architectural patterns to reuse.

## Usage Examples

### Using Review Agents

```python
from agents.review.security_sentinel import SecuritySentinel
from utils.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
agent = SecuritySentinel(kb=kb)  # KB context auto-injected

findings = agent.review(
    code=code_diff,
    file_path="src/auth.py"
)

for finding in findings:
    print(f"{finding.severity}: {finding.description}")
```

### Using TaskExecutor

```python
from agents.workflow.task_executor import TaskExecutor
from utils.project_context import ProjectContext

context = ProjectContext().get_context()
executor = TaskExecutor()

result = executor.execute(
    task_description="Add input validation to login endpoint",
    project_context=context,
    base_dir="."
)

print(f"Success: {result.success}")
print(f"Changes: {result.changes_made}")
```

### Using FeedbackCodifier

```python
from agents.workflow.feedback_codifier import FeedbackCodifier

codifier = FeedbackCodifier()

learning = codifier.predict(
    feedback="Always use prepared statements for SQL queries",
    source="security_review"
)

# Auto-saved to KB
kb.save_learning(learning)
```

## Agent Configuration

Agents use the global DSPy configuration from `config.py`:

```python
import dspy
from config import configure_dspy

configure_dspy()  # Loads from .env

# Now all agents use configured LLM
agent = SecuritySentinel()
```

## Extending Agents

To create a new review agent:

```python
import dspy
from typing import List

class MyCustomReviewer(dspy.Module):
    def __init__(self, kb=None):
        super().__init__()
        self.kb = kb
        self.reviewer = dspy.ChainOfThought("code, context -> findings")
    
    def forward(self, code: str, file_path: str = ""):
        kb_context = self.kb.retrieve_relevant(f"custom review {file_path}") if self.kb else ""
        
        result = self.reviewer(
            code=code,
            context=kb_context
        )
        
        return result.findings
```

Then register it in `workflows/review.py`:

```python
review_agents = [
    SecuritySentinel(kb=kb),
    PerformanceOracle(kb=kb),
    MyCustomReviewer(kb=kb),  # Add your agent
    # ...
]
```
