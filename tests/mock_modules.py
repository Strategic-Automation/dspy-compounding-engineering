import sys
from unittest.mock import MagicMock


def patch_all():
    mocks = [
        "dspy",
        "litellm",
        "tiktoken",
        "qdrant_client",
        "qdrant_client.models",
        "filelock",
        "rich",
        "rich.console",
        "openai",
        "pydantic",
        "pydantic_settings",
        "fastapi",
        "uvicorn",
        "dotenv",
        "fastembed",
        "tiktoken.encoding",
    ]
    for m in mocks:
        if m not in sys.modules:
            sys.modules[m] = MagicMock()


patch_all()
