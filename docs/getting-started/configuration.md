# Configuration

## Environment Setup

Then edit `.env` with your preferred LLM provider configuration.

## Command Line Configuration

You can explicitly specify which configuration file to use for any command:

```bash
uv run python cli.py --env-file custom.env work p1
```

Or set the `COMPOUNDING_ENV` environment variable:

```bash
export COMPOUNDING_ENV=~/my-configs/.env.prod
uv run python cli.py review
```

## Configuration Priority

The tool resolves configuration from multiple locations in a prioritized sequence:

1. **`--env-file` Flag**: Highest priority.
2. **`COMPOUNDING_ENV` Variable**: Environment-level override.
3. **Local `.env`**: Found in the current working directory.
4. **Tool Global Config**: `~/.config/compounding/.env`.
5. **User Home `.env`**: Final fallback.

!!! advice "Multi-Repo Best Practice"
    Store your secret API keys in the **Tool Global Config** (`~/.config/compounding/.env`) and use **Local `.env`** files in each project to specify the `DSPY_LM_MODEL` that works best for that repository's language or complexity.

## LLM Provider Options

### OpenAI

For GPT-4, GPT-3.5, or other OpenAI models:

```bash
OPENAI_API_KEY=sk-...
DSPY_LM_PROVIDER=openai
DSPY_LM_MODEL=gpt-4
```

### Anthropic Claude

For Claude 3.5 Sonnet, Haiku, or Opus:

```bash
ANTHROPIC_API_KEY=sk-ant-...
DSPY_LM_PROVIDER=anthropic
DSPY_LM_MODEL=claude-3-5-sonnet-20241022
```

### Ollama (Local)

For local, privacy-first AI using Ollama:

```bash
DSPY_LM_PROVIDER=ollama
DSPY_LM_MODEL=qwen2.5-coder:32b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

!!! info "Ollama Setup"
    1. Install Ollama from [ollama.ai](https://ollama.ai)
    2. Pull a model: `ollama pull qwen2.5-coder:32b`
    3. Ollama runs automatically on `localhost:11434`

**Recommended models for coding:**

- `qwen2.5-coder:32b` - Best quality, requires 20GB+ RAM
- `qwen2.5-coder:14b` - Good balance, 16GB+ RAM
- `deepseek-coder-v2:16b` - Alternative, good for code
- `codellama:13b` - Lighter option, 8GB+ RAM

### OpenRouter

Access multiple models through one API:

```bash
OPENROUTER_API_KEY=sk-or-...
DSPY_LM_PROVIDER=openrouter
DSPY_LM_MODEL=anthropic/claude-3.5-sonnet
```

OpenRouter provides access to:

- Anthropic Claude models
- OpenAI GPT models
- Google Gemini
- Meta Llama
- And many more...

[Get an API key](https://openrouter.ai/) | [Browse models](https://openrouter.ai/models)

## Model Selection Guide

Choose based on your priorities:

| Priority | Recommended Provider | Model |
|----------|---------------------|-------|
| **Best Quality** | Anthropic | `claude-3-5-sonnet-20241022` |
| **Fast & Good** | OpenAI | `gpt-4-turbo` |
| **Privacy** | Ollama | `qwen2.5-coder:32b` |
| **Cost-Effective** | OpenRouter | `anthropic/claude-3-haiku` |
| **Free** | Ollama | `qwen2.5-coder:7b` |

## Advanced Configuration

### Adjusting Model Parameters

You can set additional environment variables for fine-tuning:

```bash
# Temperature (0.0 - 1.0, lower = more deterministic)
DSPY_LM_TEMPERATURE=0.7

# Max tokens for responses
DSPY_LM_MAX_TOKENS=4096

# Timeout in seconds
DSPY_LM_TIMEOUT=120

# Max tokens for documentation fetching (paging support)
DOCS_MAX_TOKENS=32768
```

### Documentation Paging

When documentation content exceeds `DOCS_MAX_TOKENS`, it is automatically truncated. The agent receives a warning with instructions on how to fetch the next "page" of content using an `offset_tokens` parameter. This prevents context window overflows while still allowing access to massive documentation sites.

### Knowledge Base Settings

The knowledge base is stored in `.knowledge/` and configured automatically. To customize:

```bash
# Maximum learnings to inject into context
KB_MAX_RETRIEVED=10

# Similarity threshold for retrieval (0.0 - 1.0)
KB_SIMILARITY_THRESHOLD=0.6
```

### Embedding Configuration

Configure how the system generates vectors for semantic search and code indexing:

```bash
# Provider: openai, fastembed, openrouter, or ollama
EMBEDDING_PROVIDER=openai

# Model name (must match provider)
EMBEDDING_MODEL=text-embedding-3-small

# Custom API base if using local proxies or OpenRouter
EMBEDDING_BASE_URL=https://...
```

**Supported Local Models:**

-   **Mxbai**: `mxbai-embed-large:latest` (1024 dims) - High performance local embedding.
-   **Nomic**: `nomic-embed-text` (768 dims).
-   **Jina**: `jinaai/jina-embeddings-v2-small-en` (512 dims).

!!! tip "FastEmbed Fallback"
    If no `OPENAI_API_KEY` is found, the system automatically falls back to **FastEmbed** using the Jina small model for local execution.


## Verifying Configuration

Test your configuration:

```bash
uv run python -c "from config import get_lm; print(get_lm())"
```

You should see output indicating your LM is initialized:

```
<dspy.LM object at 0x...>
```

## Next Steps

!!! success "Configuration Complete!"
    Your environment is ready to use.

Continue to **[Quick Start](quickstart.md)** to run your first workflow.

## Troubleshooting

### API Key Not Found

If you see `API key not found`:

1. Verify `.env` file exists in the project root
2. Check the variable name matches your provider (e.g., `OPENAI_API_KEY`)
3. Ensure no quotes around the key value
4. Restart your shell or re-run `uv sync`

### Ollama Connection Error

If Ollama fails to connect:

1. Check Ollama is running: `ollama list`
2. Verify the base URL: `curl http://localhost:11434/api/version`
3. Ensure the model is pulled: `ollama pull qwen2.5-coder:32b`

### Model Not Found

Check your model name:

- OpenAI: [Available models](https://platform.openai.com/docs/models)
- Anthropic: [Available models](https://docs.anthropic.com/en/docs/models)
- Ollama: `ollama list` (shows installed models)
- OpenRouter: [Model list](https://openrouter.ai/models)
