import subprocess
import sys


def main():
    print("=> Installing dspy-compounding-engineering using uv...")

    try:
        # Install the tool via uv into an isolated environment
        print("=> Running 'uv tool install'...")
        subprocess.run(
            [
                "uv",
                "tool",
                "install",
                "--force",
                "--python",
                "python3.12",
                "git+https://github.com/Strategic-Automation/dspy-compounding-engineering.git",
            ],
            check=True,
        )

        # Update shell path to ensure tool is discoverable
        print("=> Running 'uv tool update-shell'...")
        subprocess.run(["uv", "tool", "update-shell"], check=True)

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Installation failed with exit code {e.returncode}.")
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: 'uv' command not found. Ensure 'uv' was installed properly.")
        sys.exit(1)

    print("==========================================================")
    print("✅ Installation Complete!")
    print("The 'compounding' CLI has been installed into an isolated environment.")
    print("")
    print("You may need to restart your terminal or run:")
    print("  source ~/.bashrc  (or ~/.zshrc, etc.)")
    print("to ensure the tool is in your PATH.")
    print("")
    print("Try running:")
    print("  compounding --help")
    print("==========================================================")


if __name__ == "__main__":
    main()
