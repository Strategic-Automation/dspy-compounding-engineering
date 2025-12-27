from utils.io.safe import run_safe_command

def test_command_allowlist():
    """Manual/Automated check for command allowlist."""
    try:
        print("Attempting to run unauthorized command: ls")
        run_safe_command(["ls"])
        raise RuntimeError("ERROR: Unauthorized command was allowed.")
    except ValueError as e:
        print(f"SUCCESS: Unauthorized command was blocked: {e}")

    try:
        print("\nAttempting to run authorized command: git status")
        run_safe_command(["git", "status"], capture_output=True)
        print("SUCCESS: Authorized command was allowed.")
    except ValueError as e:
        raise RuntimeError(f"ERROR: Authorized command was blocked: {e}")

if __name__ == "__main__":
    test_command_allowlist()
