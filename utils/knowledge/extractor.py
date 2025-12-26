"""
Learning Extraction Helper Module

Provides reusable functions for extracting and codifying learnings
across all workflows (review, triage, work).
"""

import dspy
from rich.console import Console

from agents.workflow.feedback_codifier import FeedbackCodifier

from .core import KnowledgeBase

console = Console()


def codify_learning(
    context: str,
    source: str,
    category: str,
    metadata: dict = None,
    silent: bool = False,
) -> bool:
    """
    Extract and codify learnings from any workflow stage.

    Args:
        context: The content to analyze for learnings
        source: Source of the learning (e.g., "review", "triage", "work")
        category: Category for the learning (e.g., "code-review", "triage", "work")
        metadata: Optional metadata to attach to the learning
        silent: If True, don't print status messages

    Returns:
        True if learning was successfully codified, False otherwise
    """
    try:
        if not silent:
            console.print(f"[dim cyan]Codifying {category} learnings...[/dim cyan]")

        # Run FeedbackCodifier Agent with Typed Output
        codifier = dspy.ChainOfThought(FeedbackCodifier)
        result = codifier(
            feedback_content=context,
            feedback_source=source,
            project_context="",
        )

        # Result should already be the Pydantic object
        codified_obj = result.codified_output

        if not codified_obj:
            if not silent:
                console.print(
                    f"[dim yellow]⚠ Empty response from FeedbackCodifier for {category}"
                    "[/dim yellow]"
                )
            return False

        # Convert Pydantic model to dict
        codified_data = codified_obj.model_dump()

        # Add metadata
        codified_data["original_feedback"] = context[:1000]  # Truncate to avoid bloat
        codified_data["source"] = source
        codified_data["category"] = category

        if metadata:
            codified_data.update(metadata)

        # Save to Knowledge Base
        kb = KnowledgeBase()
        kb.save_learning(codified_data, silent=silent)

        if not silent:
            console.print(f"[dim green]✓ Codified {category} learnings[/dim green]")

        return True

    except Exception as e:
        if not silent:
            console.print(f"[yellow]⚠ Could not codify learning: {e}[/yellow]")
        return False


def _group_findings_by_agent(findings: list) -> dict[str, list]:
    """Group findings by agent name."""
    by_agent = {}
    for finding in findings:
        agent = finding.get("agent", "Unknown")
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(finding)
    return by_agent


def _build_review_context(findings: list, todos_created: int, by_agent: dict) -> str:
    """Build the markdown context for learning extraction."""
    summary_parts = [
        "# Code Review Analysis\n",
        f"Total findings: {len(findings)} from {len(by_agent)} agents",
        f"Actionable items created: {todos_created}\n",
    ]

    summary_parts.append("\n## Findings by Agent Category:\n")
    for agent, agent_findings in sorted(by_agent.items()):
        summary_parts.append(f"\n### {agent} ({len(agent_findings)} findings)")
        for finding in agent_findings:
            review_text = str(finding.get("review", ""))
            if review_text:
                summary_parts.append(f"\n{review_text[:800]}...")

    summary_parts.append("\n\n## Pattern Extraction Focus:")
    summary_parts.extend(
        [
            "- Code quality patterns identified (naming, structure, organization)",
            "- Architectural decisions and principles",
            "- Security vulnerabilities or concerns",
            "- Performance optimization opportunities",
            "- Best practices violations or confirmations",
            "- Common anti-patterns to avoid",
            "- Reusable solutions or approaches",
        ]
    )
    return "\n".join(summary_parts)


def codify_review_findings(findings: list, todos_created: int, silent: bool = False) -> None:
    """
    Extract learnings from code review findings.

    This captures code patterns, architectural insights, and best practices
    identified during the review process.

    Args:
        findings: List of findings from review agents
        todos_created: Number of todos created from the review
        silent: If True, suppress verbose output messages
    """
    if not findings:
        return

    by_agent = _group_findings_by_agent(findings)
    context = _build_review_context(findings, todos_created, by_agent)

    # Codify with emphasis on extracting reusable patterns
    success = codify_learning(
        context=context,
        source="review",
        category="code-review-patterns",
        metadata={
            "findings_count": len(findings),
            "todos_created": todos_created,
            "agents_involved": list(by_agent.keys()),
        },
        silent=silent,
    )

    if success and not silent:
        console.print(
            f"[dim green]✓ Codified code review patterns from {len(findings)} findings[/dim green]"
        )


def codify_triage_decision(
    finding_content: str,
    decision: str,
    reason: str = None,
    proposed_solution: str = None,
) -> None:
    """
    Extract learnings from a triage decision.

    Args:
        finding_content: The content that was triaged
        decision: The decision made (approved, rejected, completed, etc.)
        reason: Reason for the decision
        proposed_solution: Proposed solution if available
    """
    context_parts = [
        f"Triage Decision: {decision}",
    ]

    if reason:
        context_parts.append(f"Reason: {reason}")

    if proposed_solution:
        context_parts.append(f"Proposed Solution: {proposed_solution}")

    # Include excerpt of finding (truncated)
    context_parts.append(f"\nFinding (excerpt): {finding_content[:500]}")

    context = "\n".join(context_parts)

    codify_learning(
        context=context,
        source="triage",
        category="triage-decisions",
        metadata={
            "decision": decision,
        },
        silent=True,  # Don't spam during batch triage
    )


def codify_work_outcome(
    todo_id: str,
    todo_slug: str,
    resolution_summary: str,
    operations_count: int,
    success: bool,
) -> None:
    """
    Extract learnings from a work resolution outcome.

    Args:
        todo_id: ID of the resolved todo
        todo_slug: Slug/description of the todo
        resolution_summary: Summary of how it was resolved
        operations_count: Number of operations performed
        success: Whether resolution was successful
    """
    context = f"""
Resolved Todo: {todo_slug} (ID: {todo_id})
Status: {"Success" if success else "Failed"}
Resolution: {resolution_summary}
Operations: {operations_count} changes made
"""

    codify_learning(
        context=context,
        source="work",
        category="work-resolutions",
        metadata={
            "todo_id": todo_id,
            "success": success,
            "operations_count": operations_count,
        },
    )


def codify_batch_triage_session(
    approved_count: int,
    skipped_count: int,
    total_count: int,
    approved_todos: list = None,
) -> None:
    """
    Extract learnings from an entire triage session.

    Args:
        approved_count: Number of items approved
        skipped_count: Number of items skipped
        total_count: Total items triaged
        approved_todos: List of approved todo filenames
    """
    context = f"""
Triage Session Summary:
- Total items: {total_count}
- Approved: {approved_count} ({approved_count / total_count * 100:.1f}%)
- Skipped: {skipped_count} ({skipped_count / total_count * 100:.1f}%)

Approved todos:
{chr(10).join(["- " + t for t in (approved_todos or [])])}
"""

    codify_learning(
        context=context,
        source="triage",
        category="triage-sessions",
        metadata={
            "approved_count": approved_count,
            "skipped_count": skipped_count,
            "total_count": total_count,
        },
    )
