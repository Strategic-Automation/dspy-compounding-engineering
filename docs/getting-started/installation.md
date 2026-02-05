# Installation

## Prerequisites

### Install uv

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver written in Rust. It's required for this project.

=== "Linux/macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "pip"

    ```bash
    pip install uv
    ```

### Python Version

This project requires **Python 3.10 or higher**. Check your version:

```bash
python --version
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Strategic-Automation/dspy-compounding-engineering.git
cd dspy-compounding-engineering
```

### 2. Install Dependencies

Using `uv`, dependencies are automatically managed:

```bash
uv sync
```

This will:

- Create a virtual environment in `.venv/`
- Install all required dependencies from `pyproject.toml`
- Lock dependencies in `uv.lock`

### 3. Install Development Dependencies (Optional)

For documentation and testing:

```bash
uv sync --group dev
```

This adds:

- MkDocs and Material theme for documentation
- pytest and coverage tools
- Ruff for linting

### 4. High-Fidelity Documentation Fetching (Optional)

For robust fetching from JS-heavy or interactive documentation sites, you should install Playwright browsers:

```bash
uv run playwright install chromium
```

!!! tip
    If Playwright is not installed or browsers are missing, the system will automatically fall back to high-quality conversion via Jina AI or basic static scraping.

## Next Steps

!!! success "Installation Complete!"
    You're ready to configure your environment and start using the tool.

Continue to:

- **[Configuration](configuration.md)** - Set up your LLM provider
- **[Quick Start](quickstart.md)** - Run your first workflow

## Troubleshooting

### uv Command Not Found

After installation, you may need to restart your shell or source your profile:

```bash
# Bash/Zsh
source ~/.bashrc  # or ~/.zshrc

# Fish
source ~/.config/fish/config.fish
```

### Python Version Issues

If `uv sync` fails due to Python version, install Python 3.10+:

=== "Ubuntu/Debian"

    ```bash
    sudo apt update
    sudo apt install python3.10
    ```

=== "macOS (Homebrew)"

    ```bash
    brew install python@3.10
    ```

=== "Windows"

    Download from [python.org](https://www.python.org/downloads/)

### Dependency Conflicts

If you encounter dependency resolution issues:

```bash
# Clear the uv cache
uv cache clean

# Retry sync
uv sync --refresh
```

## Verifying Installation

Test that everything is installed correctly:

```bash
uv run python cli.py --help
```

You should see the CLI help output with available commands.
