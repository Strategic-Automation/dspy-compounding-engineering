import dspy

from agents.schema import RepoResearchReport
from utils.agent.tools import get_research_tools
from utils.io.logger import logger


class RepoResearchAnalyst(dspy.Signature):
    """
    You are an expert repository analyst. Your mission is to provide CRITICAL local context
    about the repository structure, conventions, and patterns to guide subsequent research.

    **STRICT OUTPUT PROTOCOL:**
    1. Provide ONLY the requested fields.
    2. Use `[[ ## next_thought ## ]]` followed by your reasoning.
    3. Use `[[ ## next_tool_name ## ]]` followed by the tool name.
    4. Use `[[ ## next_tool_args ## ]]` followed by a JSON dict of arguments.
    5. CRITICAL: Always use DOUBLE brackets `[[` and `]]`. Do NOT use single brackets.
    6. Do NOT include notes or instructions like "# note: ..." in output fields.

    **Core Focus:**
    - Map repository structure and key directories.
    - Identify architecture patterns and coding standards.
    - Discover templates and contribution documentation.
    - Document local implementation patterns.

    **Example Step:**
    [[ ## next_thought ## ]] I need to find the architecture docs.
    [[ ## next_tool_name ## ]] search_codebase
    [[ ## next_tool_args ## ]] {"query": "ARCHITECTURE.md"}
    """

    feature_description = dspy.InputField(
        desc="The feature or task description to research context for"
    )
    research_report: RepoResearchReport = dspy.OutputField(desc="The repository research report")


class RepoResearchAnalystModule(dspy.Module):
    """
    Module that implements RepoResearchAnalyst using dspy.ReAct for
    comprehensive repository analysis. Uses centralized tools from
    utils/agent/tools.py for codebase exploration.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        from config import settings

        self.tools = get_research_tools(base_dir)
        self.agent = dspy.ReAct(
            RepoResearchAnalyst, tools=self.tools, max_iters=settings.agent_max_iters
        )

    def forward(self, feature_description: str):
        logger.info(f"Starting Repo Research for: {feature_description}")
        return self.agent(feature_description=feature_description)
