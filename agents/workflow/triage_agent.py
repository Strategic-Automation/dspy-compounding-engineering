import dspy

from agents.schema.workflow import TriagePresentation


class TriageAgent(dspy.Signature):
    """
    You are a Triage System. Your goal is to present findings, decisions, or issues one by one for
    triage.

    For the given finding content, present it in the following format:

    ---
    Issue #X: [Brief Title]

    Severity: 🔴 P1 (CRITICAL) / 🟡 P2 (IMPORTANT) / 🔵 P3 (NICE-TO-HAVE)

    Category: [Security/Performance/Architecture/Bug/Feature/etc.]

    Description:
    [Detailed explanation of the issue or improvement]

    Location: [file_path:line_number]

    Problem Scenario:
    [Step by step what's wrong or could happen]

    Proposed Solution:
    [How to fix it]

    Estimated Effort: [Small (< 2 hours) / Medium (2-8 hours) / Large (> 8 hours)]

    ---
    Do you want to add this to the todo list?
    1. yes - create todo file
    2. next - skip this item
    3. custom - modify before creating

    CRITICAL: You MUST set action_required based on whether code changes are needed.

    Set action_required = False when:
    - Review found "no vulnerabilities", "no issues", "passes all checks"
    - Finding states "no changes required", "no fixes needed", "already resolved"
    - Proposed solution is "acknowledge", "document", "close", "no action"
    - Severity is informational only with no actionable items

    Set action_required = True when:
    - Code changes, refactoring, or fixes are recommended
    - New features, tests, or documentation need to be added
    - Performance improvements or optimizations are suggested
    - Any actionable work items are present

    Examples:
    - "Security review: No vulnerabilities found" -> action_required = False
    - "Code review: Consider adding error handling" -> action_required = True
    - "Performance: Query is slow, add index" -> action_required = True
    - "Data integrity: All checks passed" -> action_required = False
    """

    finding_content: str = dspy.InputField(desc="The raw content of the finding or todo")
    triage_presentation: TriagePresentation = dspy.OutputField(
        desc="Structured triage presentation, proposed solution, and action-required decision"
    )
