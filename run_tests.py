"""
Test runner for PhantomLink.

Run all tests or specific test suites.
"""
import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """
    Run pytest with specified arguments.
    
    Args:
        args: List of pytest arguments (default: all tests with verbose output)
    """
    if args is None:
        args = ["-v", "--tb=short"]
    
    # Add current directory to path
    project_root = Path(__file__).parent
    
    # Run pytest
    cmd = [sys.executable, "-m", "pytest"] + args
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 70)
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run PhantomLink tests")
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific test files or directories to run"
    )
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = ["-v", "--tb=short"]
    
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    
    if args.integration:
        pytest_args.extend(["-m", "integration"])
    
    if args.fast:
        pytest_args.extend(["-m", "not slow"])
    
    if args.coverage:
        pytest_args.extend([
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    if args.files:
        pytest_args.extend(args.files)
    
    # Run tests
    return run_tests(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
