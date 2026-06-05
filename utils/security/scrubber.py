"""
Secret Scrubber module for Compounding Engineering.

This module provides functionality to redact sensitive information like API keys,
passwords, and PII from text before it's sent to an LLM.
"""

import re


class SecretScrubber:
    """
    Redacts secrets and PII from text using regex patterns.
    """

    def __init__(self):
        # Common patterns for secrets and PII
        self.patterns = {
            "openai_api_key": r"sk-[a-zA-Z0-9]{32,}",
            "anthropic_api_key": r"sk-ant-api[0-9]{2}-[a-zA-Z0-9\-_]{90,}",
            "azure_openai_key": r"[a-f0-9]{32}",
            "google_api_key": r"AIza[0-9A-Za-z-_]{35}",
            "stripe_api_key": r"(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,}",
            "aws_access_key": r"(?:AKIA|ASIA)[0-9A-Z]{16}",
            "aws_secret_key": r"(?<=[:=\s])([a-zA-Z0-9/+=]{40})(?=\s|$)",
            "slack_token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
            "ssh_private_key": (
                r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP|ENCRYPTED)? ?PRIVATE KEY(?: BLOCK)?-----"
                r"[\s\S]+?"
                r"-----END (?:RSA|OPENSSH|DSA|EC|PGP|ENCRYPTED)? ?PRIVATE KEY(?: BLOCK)?-----"
            ),
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "db_connection": (
                r"[a-zA-Z0-9+.-]+://[a-zA-Z0-9_.~-]+:[a-zA-Z0-9_.~-]+@"
                r"[a-zA-Z0-9.-]+(?::\d+)?/[a-zA-Z0-9_.~-]*"
            ),
            "generic_api_key": (
                r"(?i)(?:api[_-]?key|secret|token|password|auth|passwd|credential|pwd)"
                r"(?:\s*[:=]\s*|['\"]?[:=]['\"]?\s*)"
                r"['\"]?([a-zA-Z0-9_\-\.\/]{8,})['\"]?"
            ),
        }

        # Pre-compile regex patterns for performance
        self.compiled_patterns = {
            name: re.compile(pattern, flags=re.IGNORECASE)
            for name, pattern in self.patterns.items()
        }

    def _generic_redactor(self, match) -> str:
        """Redacts only the value portion for generic API keys."""
        full_match = match.group(0)
        secret_val = match.group(1)
        return full_match.replace(secret_val, "[REDACTED_GENERIC_API_KEY]")

    def scrub(self, text: str) -> str:
        """
        Scrub secrets and PII from the given text.
        """
        if not text:
            return ""

        scrubbed = text
        for name, compiled_pattern in self.compiled_patterns.items():
            try:
                if name == "generic_api_key":
                    scrubbed = compiled_pattern.sub(self._generic_redactor, scrubbed)
                else:
                    scrubbed = compiled_pattern.sub(f"[REDACTED_{name.upper()}]", scrubbed)
            except Exception:
                # Fallback if regex fails for some reason
                continue

        return scrubbed


# Global singleton instance
scrubber = SecretScrubber()
