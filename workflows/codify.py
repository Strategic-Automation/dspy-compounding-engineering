"""
Codify Workflow

This workflow allows users to manually codify feedback, learnings, or instructions
into the persistent knowledge base using the FeedbackCodifier agent.
"""

import dspy
from rich.console import Console
from rich.panel import Panel

from agents.workflow.feedback_codifier import FeedbackCodifier
from utils.knowledge import KnowledgeBase

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
        # Use ChainOfThought for robust typed output
        codifier = dspy.ChainOfThought(FeedbackCodifier)
        result = codifier(
            feedback_content=feedback,
            feedback_source=source,
            project_context=existing_knowledge,
        )

    # 3. Save
    try:
        # Get Pydantic object directly
        codified_obj = result.codified_output

        if not codified_obj:
            console.print("[red]Agent failed to return structured data.[/red]")
            return

        # Convert to dict
        codified_data = codified_obj.model_dump()

        # Add metadata
        codified_data["original_feedback"] = feedback
        codified_data["source"] = source

        # Save to Knowledge Base
        filepath = kb.save_learning(codified_data)

        console.print("\n[bold green]Successfully codified feedback![/bold green]")
        console.print(f"Saved to: {filepath}")

        # Display summary
        console.print("\n[bold]Improvements Identified:[/bold]")
        for imp in codified_data.get("codified_improvements", []):
            # Handle Pydantic model dump which returns dicts
            title = imp.get("title", "Untitled")
            imp_type = imp.get("type", "item").upper()
            console.print(f"- [{imp_type}] {title}")

    except Exception as e:
        console.print(f"[red]Error saving to knowledge base: {e}[/red]")
