"""
Test runner script for Financial Email Agent

This script runs all tests with coverage reporting.
"""

import sys
import subprocess
from pathlib import Path


def run_tests(test_type="all", verbose=True):
    """
    Run tests with pytest.
    
    Args:
        test_type: Type of tests to run ("unit", "integration", or "all")
        verbose: Whether to run in verbose mode
    """
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path based on type
    if test_type == "unit":
        cmd.append("tests/unit")
    elif test_type == "integration":
        cmd.append("tests/integration")
    else:
        cmd.append("tests")
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    cmd.extend([
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])
    
    # Add color output
    cmd.append("--color=yes")
    
    print("=" * 70)
    print(f"Running {test_type} tests...")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}")
    print("=" * 70)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except FileNotFoundError:
        print("\nError: pytest not found. Please install test dependencies:")
        print("  pip install -r requirements-dev.txt")
        return 1


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Financial Email Agent tests")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration"],
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Run in quiet mode (less verbose)"
    )
    
    args = parser.parse_args()
    
    return_code = run_tests(
        test_type=args.test_type,
        verbose=not args.quiet
    )
    
    if return_code == 0:
        print("\n" + "=" * 70)
        print("[SUCCESS] All tests passed!")
        print("=" * 70)
        print("\nCoverage report generated in: htmlcov/index.html")
    else:
        print("\n" + "=" * 70)
        print("[FAILED] Some tests failed")
        print("=" * 70)
    
    return return_code


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
