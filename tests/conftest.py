"""
Configuration for pytest.

Sets up test environment and shared fixtures.
"""
import pytest
from pathlib import Path


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


@pytest.fixture(scope="session")
def data_path():
    """Path to test data file."""
    return Path(__file__).parent.parent / "data" / "raw" / "mc_maze.nwb"


@pytest.fixture(scope="session")
def check_data_exists(data_path):
    """Check if test data exists, skip tests if not."""
    if not data_path.exists():
        pytest.skip(f"Test data not found at {data_path}")
