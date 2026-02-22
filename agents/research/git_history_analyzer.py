import dspy

from agents.schema import GitHistoryReport
from utils.agent.tools import get_research_tools
from utils.io.logger import logger


class GitHistoryAnalyzer(dspy.Signature):
    """
    You are an expert Git History Analyzer, a master of archaeological code analysis.
    Your mission is to uncover the hidden stories within git history, tracing code evolution,
    and identifying patterns that inform current development decisions.
    
    **STRICT OUTPUT PROTOCOL:**
    1. Provide ONLY the requested fields.
    2. Use `[[ ## next_thought ## ]]` followed by your reasoning.
    3. Use `[[ ## next_tool_name ## ]]` followed by the tool name.
    4. Use `[[ ## next_tool_args ## ]]` followed by a JSON dict of arguments.
    5. CRITICAL: Always use DOUBLE brackets `[[` and `]]`. Do NOT use single brackets.
    6. Do NOT include notes or instructions like "# note: ..." in output fields.

    **Tools Available:**
    - `git_log_search`: Search for specific strings across all commits to see when code was added or removed.
    - `git_blame`: Check who authored specific lines in a file and when.
    - `search_codebase`: Find where specific logic currently lives.

    **Goal:**
    Investigate the historical context of the requested feature. Find out if it was attempted before,
    why related architectural decisions were made, and how the core files have evolved.
    Structure your findings into the `historical_report`.
    """

    feature_description = dspy.InputField(desc="The feature or task description to research context for")
    historical_report: GitHistoryReport = dspy.OutputField(
        desc="A detailed history and evolution analysis report"
    )


class GitHistoryAnalyzerModule(dspy.Module):
    """
    Module that implements GitHistoryAnalyzer using dspy.ReAct for
    comprehensive historical analysis using git log and blame tools.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        from config import settings

        self.tools = get_research_tools(base_dir)
        self.agent = dspy.ReAct(
            GitHistoryAnalyzer, tools=self.tools, max_iters=settings.agent_max_iters
        )

    def forward(self, feature_description: str):
        logger.info(f"Starting Git History Research for: {feature_description}")
        return self.agent(feature_description=feature_description)
