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
                r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP|ENCRYPTED)? ?PRIVATE KEY(?: BLOCK)?-----[\s\S]+?"
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

    def scrub(self, text: str) -> str:
        """
        Scrub secrets and PII from the given text.
        """
        if not text:
            return ""

        scrubbed = text
        for name, pattern in self.patterns.items():
            try:
                if name == "generic_api_key":
                    # For generic keys, we only want to redact the value group
                    def create_redactor(redact_name):
                        def redact_value(match):
                            full_match = match.group(0)
                            secret_val = match.group(1)
                            msg = f"[REDACTED_{redact_name.upper()}]"
                            return full_match.replace(secret_val, msg)

                        return redact_value

                    scrubbed = re.sub(pattern, create_redactor(name), scrubbed, flags=re.IGNORECASE)
                else:
                    scrubbed = re.sub(
                        pattern, f"[REDACTED_{name.upper()}]", scrubbed, flags=re.IGNORECASE
                    )
            except Exception:
                # Fallback if regex fails for some reason
                continue

        return scrubbed


# Global singleton instance
scrubber = SecretScrubber()
