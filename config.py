import os

import dspy
from dotenv import load_dotenv

load_dotenv()


def configure_dspy():
    provider = os.getenv("DSPY_LM_PROVIDER", "openai")
    model_name = os.getenv("DSPY_LM_MODEL", "gpt-4o")

    if provider == "openai":
        lm = dspy.LM(model=model_name, api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "anthropic":
        lm = dspy.LM(
            model=f"anthropic/{model_name}", api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    elif provider == "ollama":
        # Use litellm's native Ollama support
        # Format: ollama/model_name
        lm = dspy.LM(model=f"ollama/{model_name}")
    elif provider == "openrouter":
        # [HIGHLIGHT] OpenRouter Configuration
        # OpenRouter provides access to many models via an OpenAI-compatible API.
        # Set DSPY_LM_MODEL to "provider/model-name" (e.g., "anthropic/claude-3-opus")
        # Ensure OPENROUTER_API_KEY is set in your .env file.
        lm = dspy.LM(
            model=f"openai/{model_name}",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            api_base="https://openrouter.ai/api/v1",
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    dspy.settings.configure(lm=lm)
