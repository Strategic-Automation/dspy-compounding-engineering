"""
Learning Extraction Helper Module

Provides reusable functions for extracting and codifying learnings
across all workflows (review, triage, work).
"""

import json
import re

import dspy
from rich.console import Console

from agents.workflow.feedback_codifier import FeedbackCodifier
from utils.knowledge_base import KnowledgeBase

console = Console()


def codify_learning(
    context: str,
    source: str,
    category: str,
    metadata: dict = None,
    silent: bool = False
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
        
        # Run FeedbackCodifier Agent
        codifier = dspy.Predict(FeedbackCodifier)
        result = codifier(
            feedback_content=context,
            feedback_source=source,
            project_context="",
        )
        
        # Parse JSON from response
        json_str = result.codification_json
        
        # Check for empty response
        if not json_str or not json_str.strip():
            if not silent:
                console.print(
                    f"[dim yellow]⚠ Empty response from FeedbackCodifier for {category}[/dim yellow]"
                )
            return False
        
        # Handle markdown code blocks
        if "```json" in json_str:
            json_match = re.search(r"```json\s*(.*?)\s*```", json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
        elif "```" in json_str:
            json_match = re.search(r"```\s*(.*?)\s*```", json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
        
        # Try to parse JSON
        codified_data = json.loads(json_str)
        
        # Validate that we got something useful
        if not isinstance(codified_data, dict):
            if not silent:
                console.print(
                    f"[dim yellow]⚠ Invalid codification format for {category}[/dim yellow]"
                )
            return False
        
        # Add metadata
        codified_data["original_feedback"] = context[:1000]  # Truncate to avoid bloat
        codified_data["source"] = source
        codified_data["category"] = category
        
        if metadata:
            codified_data.update(metadata)
        
        # Save to Knowledge Base
        kb = KnowledgeBase()
        kb.add_learning(codified_data)
        
        if not silent:
            console.print(f"[dim green]✓ Codified {category} learnings[/dim green]")
        
        return True
        
    except json.JSONDecodeError as e:
        if not silent:
            console.print(
                f"[yellow]⚠ Could not parse codification JSON: {e}[/yellow]"
            )
        return False
    except Exception as e:
        if not silent:
            console.print(f"[yellow]⚠ Could not codify learning: {e}[/yellow]")
        return False


def codify_review_findings(findings: list, todos_created: int) -> None:
    """
    Extract learnings from code review findings.
    
    This captures code patterns, architectural insights, and best practices
    identified during the review process.
    
    Args:
        findings: List of findings from review agents
        todos_created: Number of todos created from the review
    """
    if not findings:
        return
    
    # Aggregate findings with full details for pattern extraction
    summary_parts = [
        "# Code Review Analysis\n",
        f"Total findings: {len(findings)} from {len(set(f.get('agent', 'Unknown') for f in findings))} agents",
        f"Actionable items created: {todos_created}\n"
    ]
    
    # Group findings by category for better pattern recognition
    by_agent = {}
    for finding in findings:
        agent = finding.get("agent", "Unknown")
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(finding)
    
    # Build comprehensive context including actual findings
    summary_parts.append("\n## Findings by Agent Category:\n")
    
    for agent, agent_findings in sorted(by_agent.items()):
        summary_parts.append(f"\n### {agent} ({len(agent_findings)} findings)")
        
        for finding in agent_findings:
            review_text = str(finding.get("review", ""))
            
            # Extract key insights (first 800 chars to capture patterns)
            if review_text:
                truncated = review_text[:800]
                summary_parts.append(f"\n{truncated}...")
    
    # Add explicit prompts for pattern extraction
    summary_parts.append("\n\n## Pattern Extraction Focus:")
    summary_parts.append("- Code quality patterns identified (naming, structure, organization)")
    summary_parts.append("- Architectural decisions and principles")
    summary_parts.append("- Security vulnerabilities or concerns")
    summary_parts.append("- Performance optimization opportunities")
    summary_parts.append("- Best practices violations or confirmations")
    summary_parts.append("- Common anti-patterns to avoid")
    summary_parts.append("- Reusable solutions or approaches")
    
    context = "\n".join(summary_parts)
    
    # Codify with emphasis on extracting reusable patterns
    success = codify_learning(
        context=context,
        source="review",
        category="code-review-patterns",
        metadata={
            "findings_count": len(findings),
            "todos_created": todos_created,
            "agents_involved": list(by_agent.keys()),
        }
    )
    
    if success:
        console.print(
            f"[dim green]✓ Codified code review patterns from {len(findings)} findings[/dim green]"
        )


def codify_triage_decision(
    finding_content: str,
    decision: str,
    reason: str = None,
    proposed_solution: str = None
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
        silent=True  # Don't spam during batch triage
    )


def codify_work_outcome(
    todo_id: str,
    todo_slug: str,
    resolution_summary: str,
    operations_count: int,
    success: bool
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
Status: {'Success' if success else 'Failed'}
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
        }
    )


def codify_batch_triage_session(
    approved_count: int,
    skipped_count: int,
    total_count: int,
    approved_todos: list = None
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
- Approved: {approved_count} ({approved_count/total_count*100:.1f}%)
- Skipped: {skipped_count} ({skipped_count/total_count*100:.1f}%)

Approved todos:
{chr(10).join(['- ' + t for t in (approved_todos or [])])}
"""
    
    codify_learning(
        context=context,
        source="triage",
        category="triage-sessions",
        metadata={
            "approved_count": approved_count,
            "skipped_count": skipped_count,
            "total_count": total_count,
        }
    )
