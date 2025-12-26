"""
Token Counter module.

This module handles token counting logic using tiktoken,
with caching to improve performance on large codebases.
"""

import hashlib
from typing import Dict

import tiktoken

# Cache structure: Dict[model_name, Dict[content_hash, token_count]]
_TOKEN_CACHE: Dict[str, Dict[str, int]] = {}


class TokenCounter:
    """
    Handles token counting with caching.
    """

    def __init__(self, default_model: str = "gpt-4o"):
        self.default_model = default_model
        if default_model not in _TOKEN_CACHE:
            _TOKEN_CACHE[default_model] = {}

    def count_tokens(self, text: str, model: str = None) -> int:
        """
        Count tokens in text string.
        """
        if not text:
            return 0

        target_model = model or self.default_model

        # Check cache
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        if target_model in _TOKEN_CACHE and content_hash in _TOKEN_CACHE[target_model]:
            return _TOKEN_CACHE[target_model][content_hash]

        # Get encoding
        try:
            encoding = tiktoken.encoding_for_model(target_model)
        except KeyError:
            # Fallback for unknown models (e.g. ollama)
            encoding = tiktoken.get_encoding("cl100k_base")

        count = len(encoding.encode(text))

        # Update cache
        if target_model not in _TOKEN_CACHE:
            _TOKEN_CACHE[target_model] = {}
        _TOKEN_CACHE[target_model][content_hash] = count

        return count

    def estimate_tokens(self, text: str) -> int:
        """
        Fast estimation (char count / 4).
        Good for rough checks before expensive counting.
        """
        return len(text) // 4
