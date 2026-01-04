# Agents API Reference

The system uses specialized DSPy agents for different tasks. Each agent is implemented as a DSPy `Signature` or `Module`.

## Review Agents

Located in `agents/review/`, these agents analyze code for specific concerns. All review agents now return structured data using Pydantic models inheriting from `ReviewReport`.

### Common Schema

All agents return a report inheriting from `ReviewReport` containing:
- `summary`: High-level executive summary.
- `analysis`: detailed technical analysis.
- `findings`: List of `ReviewFinding` objects (category, severity, description, solution, etc.).
- `action_required`: Boolean indicating if manual intervention is needed.

### SecuritySentinel
**Module**: `agents/review/security_sentinel.py`

Detects security vulnerabilities.

**Unique Fields**:
- `risk_matrix`: A text-based matrix assessing likelihood and impact.

**Output**: `SecurityReport`

### PerformanceOracle
**Module**: `agents/review/performance_oracle.py`

Identifies performance issues and optimization opportunities.

**Unique Fields**:
- `scalability_assessment`: Analysis of how the code scales.
- `optimization_opportunities`: List of specific performance wins.

**Output**: `PerformanceReport`

### ArchitectureStrategist
**Module**: `agents/review/architecture_strategist.py`

Reviews system design, patterns, and SOLID principles.

**Unique Fields**:
- `risk_analysis`: Analysis of architectural risks and debt.

**Output**: `ArchitectureReport`

### DataIntegrityGuardian
**Module**: `agents/review/data_integrity_guardian.py`

Ensures data consistency, privacy compliance, and safe migrations.

**Unique Fields**:
- `migration_analysis`: Safety check for schema changes.
- `privacy_compliance`: GDPR/CCPA compliance check.
- `rollout_strategy`: Recommended deployment strategy for data changes.

**Output**: `DataIntegrityReport`

### CodeSimplicityReviewer
**Module**: `agents/review/code_simplicity_reviewer.py`

Focuses on code readability, complexity reduction, and specific "Simplicity Wins".

**Unique Fields**:
- `core_purpose`: The deduced primary goal of the code.
- `final_assessment`: Overall simplicity rating.

**Output**: `SimplicityReport`

### DhhRailsReviewer
**Module**: `agents/review/dhh_rails_reviewer.py`

Enforces "The Rails Way" conventions and DHH-style coding philosophies.

**Unique Fields**:
- `complexity_analysis`: Evaluation of necessary vs accidental complexity.
- `final_verdict`: Pass/Fail/Warn verdict.

**Output**: `DhhReviewReport`

### KieranRailsReviewer
**Module**: `agents/review/kieran_rails_reviewer.py`

Checks for specific Rails patterns and conventions preferred by the team (Kieran's style).

**Unique Fields**:
- `convention_score`: Quantitative score (0-100) of adherence to conventions.

**Output**: `KieranReport`

### KieranPythonReviewer
**Module**: `agents/review/kieran_python_reviewer.py`

Enforces Pythonic idioms and project-specific Python standards.

**Unique Fields**:
- `pythonic_score`: Quantitative score (0-100) of Pythonic code quality.

**Output**: `KieranPythonReport`

### KieranTypescriptReviewer
**Module**: `agents/review/kieran_typescript_reviewer.py`

Reviews TypeScript code for type safety and best practices.

**Unique Fields**:
- `typesafety_score`: Quantitative score (0-100) of type safety (e.g., use of `any`).

**Output**: `KieranTSReport`

### PatternRecognitionSpecialist
**Module**: `agents/review/pattern_recognition_specialist.py`

Identifies design patterns and anti-patterns.

**Unique Fields**:
- `naming_convention_analysis`: Review of variable/function naming.
- `duplication_metrics`: Assessment of code duplication.

**Output**: `PatternReport`

### AgentNativeReviewer
**Module**: `agents/review/agent_native_reviewer.py`

Ensures features are accessible to agents (Action/Context parity).

**Unique Fields**:
- `agent_native_score`: Assessment of agent capability.
- `capability_analysis`: Analysis of user vs agent capability gaps.

**Output**: `AgentNativeReport`

### JulikFrontendRacesReviewer
**Module**: `agents/review/julik_frontend_races_reviewer.py`

Detects race conditions, timing issues, and frontend concurrency bugs.

**Unique Fields**:
- `timing_analysis`: Critique of promise/timer usage.

**Output**: `JulikReport`

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
from utils.knowledge import KnowledgeBase

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
from utils.context import ProjectContext

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

1. Define your output schema inheriting from `ReviewReport`.
2. Define your signature using the schema.
3. Subclass `ReviewAgent` (or implement `dspy.Module` similar to existing agents).

```python
import dspy
from pydantic import Field
from agents.review.schema import ReviewReport, ReviewFinding

# 1. Define Output Schema
class MyCustomReport(ReviewReport):
    custom_metric: str = Field(..., description="Some custom analysis metric")

# 2. Define Signature
class MyCustomReviewSignature(dspy.Signature):
    """Review code for custom concerns."""
    code_diff: str = dspy.InputField(desc="Code changes")
    review_report: MyCustomReport = dspy.OutputField(desc="Structured review report")

# 3. Implement Agent
class MyCustomReviewer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.reviewer = dspy.TypedPredictor(MyCustomReviewSignature)
    
    def forward(self, code_diff: str):
        return self.reviewer(code_diff=code_diff).review_report
```

Then register it in `workflows/review.py`:

```python
review_agents = [
    # ...
    ("My Custom Reviewer", MyCustomReviewer),
]
```
