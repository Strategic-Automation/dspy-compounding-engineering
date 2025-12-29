"""
Knowledge Base Augmented DSPy Module

This module provides a DSPy Module that automatically injects knowledge base
context into LLM calls, enabling true compounding engineering where past
learnings inform future operations.

Based on DSPy best practices: instead of extending dspy.Predict, we create
a custom dspy.Module that wraps it and injects KB context in the forward method.
"""

from typing import Any, List, Optional

import dspy

from .core import KnowledgeBase


class KBPredict(dspy.Module):
    """
    DSPy Module that wraps dspy.Predict with automatic KB injection.
    Simplified: all logic inlined, dropped base class and unused CoT.
    """

    def __init__(
        self,
        signature: Any,
        kb_tags: Optional[List[str]] = None,
        kb_query: Optional[str] = None,
        inject_kb: bool = True,
        **kwargs,
    ):
        super().__init__()
        self.kb_tags = kb_tags or []
        self.kb_query = kb_query
        self.inject_kb = inject_kb

        # Support both signatures (wrapped in Predict) and direct Modules
        if (
            isinstance(signature, type)
            and issubclass(signature, dspy.Module)
            and not issubclass(signature, dspy.Signature)
        ):
            self.predictor = signature(**kwargs)
        else:
            self.predictor = dspy.Predict(signature, **kwargs)

    def forward(self, **kwargs):
        if not self.inject_kb:
            return self.predictor(**kwargs)
        augmented_kwargs = self._inject_kb(kwargs)
        return self.predictor(**augmented_kwargs)

    def _inject_kb(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        # Cache KB instance to avoid repeated initialization
        if not hasattr(self, "_kb"):
            self._kb = KnowledgeBase()
        kb = self._kb

        query = self.kb_query
        if not query:
            query_parts = [str(v)[:500] for v in kwargs.values() if isinstance(v, str)]
            query = " ".join(query_parts)[:1000]

        kb_context = kb.get_context_string(query=query, tags=self.kb_tags)

        kwargs = kwargs.copy()

        if kb_context and kb_context != "No relevant past learnings found.":
            for key in kwargs:
                if isinstance(kwargs[key], str) and len(kwargs[key]) > 10:
                    kwargs[key] = self._format_kb_injection(kb_context, kwargs[key])
                    break

        return kwargs

    def _format_kb_injection(self, kb_context: str, original_input: str) -> str:
        separator = "\n\n" + "=" * 80 + "\n\n"

        formatted = (
            "## Past Learnings (Auto-Injected from Knowledge Base)\n\n"
            "The following patterns and learnings have been codified from past work.\n"
            f"Apply these automatically when relevant to the current task:\n\n{kb_context}\n\n"
            f"{separator}\n\n## Current Task\n\n{original_input}"
        )
        return formatted
