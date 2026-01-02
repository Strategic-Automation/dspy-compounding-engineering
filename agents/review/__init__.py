"""
Agents.review package.
All agents are discovered dynamically via workflows/review.py.
"""

# Shared constants for agent metadata validation
VALID_CATEGORIES = frozenset(
    {
        "code-review",
        "security",
        "performance",
        "architecture",
        "simplicity",
        "complexity",
        "agent-native",
        "rails",
        "frontend",
        "data-integrity",
    }
)

VALID_SEVERITIES = frozenset({"p1", "p2", "p3"})
