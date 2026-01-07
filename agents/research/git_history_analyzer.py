import dspy

from agents.schema import GitHistoryReport


class GitHistoryAnalyzer(dspy.Signature):
    """
    You are a Git History Analyzer, an expert in archaeological analysis of code repositories.
    Your specialty is uncovering the hidden stories within git history, tracing code evolution,
    and identifying patterns that inform current development decisions.

    Note: The current year is 2025.

    **Output Format:**

    Structure your findings into the provided GitHistoryReport schema.
    Ensure you provide a high-level `summary` of the history, a technical `analysis`
    of the code evolution, and granular `insights` for each milestone, major
    refactor, or significant architectural shift identified.
    """

    context_request = dspy.InputField(desc="The user's request for historical context or analysis.")
    git_log_output = dspy.InputField(
        desc="Output from git commands (log, blame, shortlog) relevant to the request."
    )
    historical_report: GitHistoryReport = dspy.OutputField(
        desc="A detailed history and evolution analysis report"
    )
