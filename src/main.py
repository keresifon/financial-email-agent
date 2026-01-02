"""
Financial Email Agent - Main Entry Point

This is the main entry point for the Financial Email Agent application.
It initializes the agent and starts the email monitoring process.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Main entry point for the application."""
    print("Financial Email Agent v0.1.0")
    print("=" * 50)
    print("\nInitializing agent...")
    print("\n⚠️  This is a placeholder. Implementation coming soon!")
    print("\nNext steps:")
    print("1. Configure Gmail API credentials")
    print("2. Set up MongoDB connection")
    print("3. Install and configure Ollama with Llama 3.1")
    print("4. Update configuration in config/config.yaml")
    print("\nSee docs/implementation-plan.md for detailed roadmap.")


if __name__ == "__main__":
    main()

# Made with Bob
