import dspy

from agents.schema import FrameworkDocsReport
from utils.agent.tools import get_research_tools
from utils.io.logger import logger


class FrameworkDocsResearcher(dspy.Signature):
    """
    You are a documentation specialist. Your mission is to extract practical, version-aware
    knowledge from official library/framework documentation.

    **STRICT OUTPUT PROTOCOL:**
    1. Provide ONLY the requested fields.
    2. Use `[[ ## next_thought ## ]]` followed by your reasoning.
    3. Use `[[ ## next_tool_name ## ]]` followed by the tool name.
    4. Use `[[ ## next_tool_args ## ]]` followed by a JSON dict of arguments.
    5. CRITICAL: Always use DOUBLE brackets `[[` and `]]`. Do NOT use single brackets.
    6. Do NOT include notes or instructions like "# note: ..." in output fields.

    **Core Focus:**
    - Review `previous_research` to fill technical gaps and identify version-specific needs.
    - Analyze API references, configuration options, and migration guides.
    - Highly prioritize the most recent, official documentation for the specified version.
    - Leverage high-fidelity fetching tools (like Playwright) to navigate interactive or JS-heavy docs.
    - Document practical usage examples and common implementation pitfalls.

    **Example Step:**
    [[ ## next_thought ## ]] Fetching the latest v4.x documentation for the library, as it contains critical breaking changes.
    [[ ## next_tool_name ## ]] fetch_documentation
    [[ ## next_tool_args ## ]] {"url": "https://example.com/docs/v4.0/api"}
    """

    framework_or_library = dspy.InputField(desc="The framework, library, or feature to research")
    previous_research = dspy.InputField(
        desc="Existing research findings from repo or best practices (optional)",
        default=None,
    )
    documentation_report: FrameworkDocsReport = dspy.OutputField(
        desc="The comprehensive documentation report"
    )


class FrameworkDocsResearcherModule(dspy.Module):
    """
    Module that implements FrameworkDocsResearcher using dspy.ReAct for
    thorough documentation research. Uses centralized tools from
    utils/agent/tools.py.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        from config import settings

        self.tools = get_research_tools(base_dir)
        self.agent = dspy.ReAct(
            FrameworkDocsResearcher, tools=self.tools, max_iters=settings.agent_max_iters
        )

    def forward(self, framework_or_library: str, previous_research: str = None):
        logger.info(f"Starting Framework Docs Research for: {framework_or_library}")
        return self.agent(
            framework_or_library=framework_or_library, previous_research=previous_research
        )
