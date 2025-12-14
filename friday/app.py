"""Friday - AI Coding Assistant CLI

Main entry point for the Friday conversational coding CLI.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from friday.cli import FridayCLI


def main():
    """Main entry point for Friday CLI"""
    cli = FridayCLI()
    cli.run()


if __name__ == "__main__":
    main()
