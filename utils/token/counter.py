"""
Token Counter module.

This module handles token counting logic using tiktoken,
with caching to improve performance on large codebases.
"""

import functools
import hashlib
from collections import OrderedDict

import tiktoken

# Cache structure: Dict[model_name, OrderedDict[content_hash, token_count]]
# Using OrderedDict to implement a lightweight LRU cache without external dependencies.
_TOKEN_CACHE: dict[str, OrderedDict[str, int]] = {}
_MAX_CACHE_SIZE = 10000


@functools.lru_cache(maxsize=128)
def _get_encoding(model: str) -> tiktoken.Encoding:
    """Cached retrieval of tiktoken encoding for a specific model."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback for unknown models (e.g. ollama)
        return tiktoken.get_encoding("cl100k_base")


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

        # Use MD5 hash to avoid holding large text strings in memory
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        if target_model not in _TOKEN_CACHE:
            _TOKEN_CACHE[target_model] = OrderedDict()

        cache = _TOKEN_CACHE[target_model]

        if content_hash in cache:
            # Move to end to mark as recently used
            cache.move_to_end(content_hash)
            return cache[content_hash]

        # Get encoding from our local fast lru_cache wrapper
        encoding = _get_encoding(target_model)
        count = len(encoding.encode(text))

        # Enforce LRU size limit
        if len(cache) >= _MAX_CACHE_SIZE:
            # popitem(last=False) removes the oldest (first inserted) item
            cache.popitem(last=False)

        cache[content_hash] = count

        return count
