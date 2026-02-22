#!/bin/sh
set -e

echo "=> Installing dspy-compounding-engineering using uv..."

# 1. Install uv if not available
if ! command -v uv >/dev/null 2>&1; then
    echo "=> 'uv' not found. Installing via official script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Try to source the env to add uv to PATH for this script execution
    if [ -f "$HOME/.local/bin/env" ]; then
        . "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
        . "$HOME/.cargo/env"
    fi
    
    # Fallback to direct path
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv installation failed or uv is not in PATH."
    exit 1
fi

echo "=> 'uv' is available. Proceeding with installation..."

# 2. Install dspy-compounding-engineering CLI
echo "=> Installing the CLI..."
uv tool install --force --python python3.12 git+https://github.com/Strategic-Automation/dspy-compounding-engineering.git
uv tool update-shell

echo "=========================================================="
echo "✅ Installation Complete!"
echo "The 'compounding' CLI has been installed into an isolated environment."
echo ""
echo "You may need to restart your terminal or run:"
echo "  source ~/.bashrc  (or ~/.zshrc, etc.)"
echo "to ensure the tool is in your PATH."
echo ""
echo "Try running:"
echo "  compounding --help"
echo "=========================================================="
