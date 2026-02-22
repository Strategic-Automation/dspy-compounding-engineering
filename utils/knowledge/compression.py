import logging
import os
from typing import List

import dspy


class CompressMarkdown(dspy.Signature):
    """
    Compress the given markdown content while preserving its structure, key details,
    and technical accuracy.
    Reduce the length by approximately the target ratio (e.g., 0.5 means 50% size).
    Retain all headers, code blocks, and list structures where possible.
    """

    content: str = dspy.InputField(desc="The markdown content to compress")
    ratio: float = dspy.InputField(desc="Target compression ratio (0.0 to 1.0)")
    compressed_content: str = dspy.OutputField(desc="The compressed markdown content")


class LLMKBCompressor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.compressor = dspy.ChainOfThought(CompressMarkdown)

    def _split_markdown_by_headers(self, text: str) -> List[str]:
        """
        Split markdown by H2 headers (##).
        This is a simple heuristic to process logical sections independently.
        """
        lines = text.split("\n")
        chunks = []
        current_chunk = []

        for line in lines:
            if line.startswith("## "):
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _get_cache_path(self) -> str:
        return os.path.join(".knowledge", "cache", "llm_compression_cache.json")

    def _load_cache(self) -> dict:
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                import json

                with open(cache_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict) -> None:
        cache_path = self._get_cache_path()
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        try:
            import json

            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            # Cache write failures are non-fatal; log and continue.
            logging.debug("Failed to save LLM compression cache to %s", cache_path, exc_info=True)

    def forward(self, content: str, ratio: float = 0.5) -> str:
        """
        Compresses the given markdown content with caching.
        """
        # Check cache first
        import hashlib

        content_hash = hashlib.md5(f"{content}:{ratio}".encode()).hexdigest()
        cache = self._load_cache()
        if content_hash in cache:
            return cache[content_hash]

        # Use split-compress-merge strategy
        if len(content) < 4000:
            result = self.compressor(content=content, ratio=ratio).compressed_content
        else:
            chunks = self._split_markdown_by_headers(content)
            compressed_chunks = []

            for chunk in chunks:
                if len(chunk.strip()) < 100:
                    compressed_chunks.append(chunk)
                    continue

                try:
                    res = self.compressor(content=chunk, ratio=ratio)
                    compressed_chunks.append(res.compressed_content)
                except Exception:
                    compressed_chunks.append(chunk)

            result = "\n\n".join(compressed_chunks)

        # Save to cache
        cache[content_hash] = result
        self._save_cache(cache)

        return result
