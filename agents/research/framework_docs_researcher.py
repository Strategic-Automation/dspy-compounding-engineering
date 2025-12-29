import dspy

from agents.research.schema import FrameworkDocsReport
from utils.agent.tools import get_research_tools
from utils.io.logger import logger


class FrameworkDocsResearcher(dspy.Signature):
    """
    You are a documentation specialist focused on extracting practical knowledge
    from framework and library documentation. Your mission is to analyze official
    documentation sources and synthesize actionable guidance.

    **Core Responsibilities:**

    1. **Official Documentation Analysis**
       - Navigate and analyze API references
       - Extract configuration options and best practices
       - Identify common patterns and anti-patterns

    2. **Version-Aware Research**
       - Note version-specific features or breaking changes
       - Highlight deprecated APIs or migration paths

    3. **Practical Examples**
       - Find and document working code examples
       - Identify integration patterns with other tools

    **Available Tools:**
    - `fetch_documentation(url)`: Fetch external documentation from a URL.
    - `semantic_search(query, limit)`: Vector search for relevant code by meaning.
    - `search_codebase(query, path)`: Grep-based keyword search in project files.
    - `read_file(file_path, start_line, end_line)`: Read specific file sections.

    **Output Format:**

    Structure your findings into the provided FrameworkDocsReport schema.
    Provide a high-level `summary`, a technical `analysis` of how the framework works,
    and granular `insights` for each API endpoint, guide, or best practice found.
    """

    framework_or_library = dspy.InputField(desc="The framework, library, or feature to research")
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
        self.tools = get_research_tools(base_dir)
        self.agent = dspy.ReAct(FrameworkDocsResearcher, tools=self.tools, max_iters=3)

    def forward(self, framework_or_library: str):
        logger.info(f"Starting Framework Docs Research for: {framework_or_library}")
        return self.agent(framework_or_library=framework_or_library)
