import dspy

from agents.schema import BestPracticesReport
from config import settings
from utils.agent.tools import get_research_tools
from utils.io.logger import logger


class BestPracticesResearcher(dspy.Signature):
    """
    You are an expert technology researcher. Your mission is to provide actionable
    best practices based on industry standards and repo context.

    **STRICT OUTPUT PROTOCOL:**
    1. Provide ONLY the requested fields.
    2. Use `[[ ## next_thought ## ]]` followed by your reasoning.
    3. Use `[[ ## next_tool_name ## ]]` followed by the tool name.
    4. Use `[[ ## next_tool_args ## ]]` followed by a JSON dict of arguments.
    5. CRITICAL: Always use DOUBLE brackets `[[` and `]]`. Do NOT use single brackets.
    6. Do NOT include notes or instructions like "# note: ..." in output fields.

    **Core Focus:**
    - Analyze `repo_research` to avoid redundancy.
    - Research official documentation and authoritative standards.
    - Synthesize findings into clear guidance.
    - Identify implementation patterns and anti-patterns.

    **Example Step:**
    [[ ## next_thought ## ]] Looking for Python style guides.
    [[ ## next_tool_name ## ]] internet_search
    [[ ## next_tool_args ## ]] {"query": "official python style guide PEP 8"}
    """

    topic = dspy.InputField(desc="The topic or technology to research best practices for")
    repo_research = dspy.InputField(
        desc="Existing research about the repository structure and conventions (optional)",
        default=None,
    )
    research_report: BestPracticesReport = dspy.OutputField(
        desc="The synthesized best practices report"
    )


class BestPracticesResearcherModule(dspy.Module):
    """
    Module that implements BestPracticesResearcher using dspy.ReAct for
    sophisticated reasoning over best practices. Uses centralized tools
    from utils/agent/tools.py.
    """

    def __init__(self, base_dir: str = "."):
        super().__init__()
        self.tools = get_research_tools(base_dir)
        self.agent = dspy.ReAct(
            BestPracticesResearcher, tools=self.tools, max_iters=settings.agent_max_iters
        )

    def forward(self, topic: str, repo_research: str = None):
        logger.info(f"Starting Best Practices Research for: {topic}")
        return self.agent(topic=topic, repo_research=repo_research)
