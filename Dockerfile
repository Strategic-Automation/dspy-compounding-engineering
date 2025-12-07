FROM python:3.10-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies (system-wide to avoid venv in container)
RUN uv sync --frozen --system

# Copy application code
COPY . .

# Set entrypoint
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
