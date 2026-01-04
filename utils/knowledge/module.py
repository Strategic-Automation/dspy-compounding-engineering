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

from ..io.logger import logger


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
        if isinstance(signature, dspy.Module):
            self.predictor = signature
        elif (
            isinstance(signature, type)
            and issubclass(signature, dspy.Module)
            and not issubclass(signature, dspy.Signature)
        ):
            self.predictor = signature(**kwargs)
        else:
            self.predictor = dspy.Predict(signature, **kwargs)

    @classmethod
    def wrap(cls, module: dspy.Module, kb_tags: List[str], **kwargs) -> "KBPredict":
        """Factory method to wrap an existing module with KB augmented context."""
        return cls(module, kb_tags=kb_tags, **kwargs)

    def forward(self, **kwargs):
        if not self.inject_kb:
            return self.predictor(**kwargs)

        logger.debug(f"KBPredict.forward: Injecting KB context (Tags: {self.kb_tags})")
        augmented_kwargs = self._inject_kb(kwargs)
        return self.predictor(**augmented_kwargs)

    def _inject_kb(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        # Use KnowledgeBase singleton from registry to avoid instantiation storm
        from config import registry

        kb = registry.get_kb()

        query = self.kb_query
        if not query:
            # Smart context query: combine all string inputs
            query_parts = [str(v)[:500] for v in kwargs.values() if isinstance(v, str)]
            query = " ".join(query_parts)[:1000]

        kb_context = kb.get_context_string(query=query, tags=self.kb_tags)

        kwargs = kwargs.copy()

        if kb_context and kb_context != "No relevant past learnings found.":
            # Find the largest string input to inject into
            target_key = None
            max_len = -1
            for key, val in kwargs.items():
                if isinstance(val, str) and len(val) > max_len:
                    max_len = len(val)
                    target_key = key

            if target_key:
                kwargs[target_key] = self._format_kb_injection(kb_context, kwargs[target_key])

        return kwargs

    def _format_kb_injection(self, kb_context: str, original_input: str) -> str:
        separator = "\n\n" + "=" * 80 + "\n\n"

        formatted = (
            "## Past Learnings (Auto-Injected from Knowledge Base)\n\n"
            "The following patterns and learnings have been codified from past work.\n"
            "Apply context to avoid past mistakes and follow established patterns.\n"
            "If the current task conflicts with these learnings, prioritize established project "
            "patterns found in the codebase context, but explain why in your reasoning.\n\n"
            f"{kb_context}\n\n"
            f"{separator}\n\n## Current Task\n\n{original_input}"
        )
        return formatted
