"""
Codify Workflow

This workflow allows users to manually codify feedback, learnings, or instructions
into the persistent knowledge base using the FeedbackCodifier agent.
"""

import json

import dspy
from rich.console import Console
from rich.panel import Panel

from agents.workflow.feedback_codifier import FeedbackCodifier
from utils.knowledge_base import KnowledgeBase

console = Console()


def run_codify(feedback: str, source: str = "manual_input"):
    """
    Codify feedback into the knowledge base.

    Args:
        feedback: The raw text to codify.
        source: The source of the feedback (e.g., "manual", "review", "retro").
    """
    console.print(Panel(f"Codifying Feedback from {source}", style="bold blue"))

    kb = KnowledgeBase()

    # 1. Get existing context to avoid duplicates or conflicts
    # For now, we just get a summary of what's there
    existing_knowledge = kb.get_context_string(query=feedback)

    # 2. Run FeedbackCodifier Agent
    with console.status("[cyan]Analyzing and codifying feedback...[/cyan]"):
        codifier = dspy.Predict(FeedbackCodifier)
        result = codifier(
            feedback_content=feedback,
            feedback_source=source,
            project_context=existing_knowledge,
        )

    # 3. Parse and Save
    try:
        # Extract JSON from response if needed
        json_str = result.codification_json
        if "```json" in json_str:
            import re

            match = re.search(r"```json\s*(.*?)\s*```", json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
        elif "```" in json_str:
            import re

            match = re.search(r"```\s*(.*?)\s*```", json_str, re.DOTALL)
            if match:
                json_str = match.group(1)

        codified_data = json.loads(json_str)

        # Add metadata
        codified_data["original_feedback"] = feedback
        codified_data["source"] = source

        # Save to Knowledge Base
        filepath = kb.add_learning(codified_data)

        console.print("\n[bold green]Successfully codified feedback![/bold green]")
        console.print(f"Saved to: {filepath}")

        # Display summary
        console.print("\n[bold]Improvements Identified:[/bold]")
        for imp in codified_data.get("codified_improvements", []):
            console.print(
                f"- [{imp.get('type', 'item').upper()}] {imp.get('title', 'Untitled')}"
            )

    except json.JSONDecodeError:
        console.print("[red]Failed to parse agent output as JSON.[/red]")
        console.print(f"Raw output:\n{result.codification_json}")
    except Exception as e:
        console.print(f"[red]Error saving to knowledge base: {e}[/red]")
