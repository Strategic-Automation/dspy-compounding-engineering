"""
Token Counter module.

This module handles token counting logic using tiktoken,
with caching to improve performance on large codebases.
"""

import functools

import tiktoken


# Use an unbounded LRU cache by setting maxsize=None or a large value like 10000.
# A bounded cache protects against memory bloat from long-lived processes
# processing many unique strings.
@functools.lru_cache(maxsize=10000)
def _count_tokens_cached(text: str, target_model: str) -> int:
    """
    Cached helper to count tokens using tiktoken.
    This replaces manual MD5 hashing and caching with Python's built-in, C-optimized lru_cache.
    """
    try:
        # tiktoken internally caches the Encoding object returned by encoding_for_model,
        # so calling it repeatedly is relatively fast, but caching the entire string
        # result is even faster.
        encoding = tiktoken.encoding_for_model(target_model)
    except KeyError:
        # Fallback for unknown models (e.g. ollama)
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


class TokenCounter:
    """
    Handles token counting with caching.
    """

    def __init__(self, default_model: str = "gpt-4o"):
        self.default_model = default_model

    def count_tokens(self, text: str, model: str = None) -> int:
        """
        Count tokens in text string.
        """
        if not text:
            return 0

        target_model = model or self.default_model
        return _count_tokens_cached(text, target_model)
