"""
Unit tests for data loader (data_loader.py).

Tests MC_MazeLoader functionality including lazy loading, data access,
and trial querying.
"""
import pytest
import numpy as np
from pathlib import Path
from data_loader import MC_MazeLoader


# Path to test data
DATA_PATH = Path(__file__).parent / "data" / "mc_maze.nwb"


@pytest.fixture
def loader():
    """Create a data loader instance for testing."""
    if not DATA_PATH.exists():
        pytest.skip(f"Test data not found at {DATA_PATH}")
    return MC_MazeLoader(DATA_PATH, lazy_load=True)


class TestMC_MazeLoader:
    """Test MC_MazeLoader class."""
    
    def test_initialization(self, loader):
        """Test loader initialization."""
        assert loader.file_path == DATA_PATH
        assert loader.lazy_load is True
        assert loader._io is not None  # Auto-loaded in __init__
    
    def test_open_close(self, loader):
        """Test that dataset is auto-opened and can be closed."""
        # Dataset is auto-opened in __init__
        assert loader._io is not None
        assert loader._nwb is not None
        
        # Test closing
        loader.close()
        # Note: close() doesn't set _io/_nwb to None, it just closes the file handle
    
    def test_context_manager(self):
        """Test using loader as context manager."""
        if not DATA_PATH.exists():
            pytest.skip(f"Test data not found at {DATA_PATH}")
        
        with MC_MazeLoader(DATA_PATH) as loader:
            assert loader._io is not None
            assert loader._nwb is not None
    
    def test_get_num_channels(self, loader):
        """Test getting number of channels."""
        num_channels = loader.num_channels
        assert isinstance(num_channels, int)
        assert num_channels > 0
    
    def test_get_duration(self, loader):
        """Test getting dataset duration."""
        duration = loader.duration
        assert isinstance(duration, float)
        assert duration > 0
    
    def test_get_spike_counts_at_time(self, loader):
        """Test getting spike counts for time window."""
        # Get spike counts from t=1.0s to t=1.025s (one 25ms bin)
        spike_counts = loader.get_binned_spikes(
            start_time=1.0,
            end_time=1.025,
            bin_size_ms=25.0
        )
        
        assert isinstance(spike_counts, np.ndarray)
        assert spike_counts.shape[0] >= 1  # At least one bin
        assert spike_counts.shape[1] == loader.num_channels
        
        # Spike counts should be non-negative integers
        assert np.all(spike_counts >= 0)
        assert spike_counts.dtype == int
    
    def test_get_spike_counts_different_bin_sizes(self, loader):
        """Test spike counts with different bin sizes."""
        counts_25ms = loader.get_binned_spikes(1.0, 2.0, bin_size_ms=25.0)
        counts_50ms = loader.get_binned_spikes(1.0, 2.0, bin_size_ms=50.0)
        
        # Different bin sizes should produce different shapes
        assert counts_25ms.shape[0] > counts_50ms.shape[0]
        # Total spike count should be similar
        assert abs(counts_25ms.sum() - counts_50ms.sum()) < counts_25ms.sum() * 0.1
    
    def test_get_cursor_position(self, loader):
        """Test getting cursor position via kinematics."""
        kinematics = loader.get_kinematics(start_time=1.0, end_time=1.1)
        
        assert isinstance(kinematics, dict)
        assert 'x' in kinematics
        assert 'y' in kinematics
        positions_x = kinematics['x']
        positions_y = kinematics['y']
        # Positions should be reasonable (not NaN or infinite)
        assert not np.any(np.isnan(positions_x))
        assert not np.any(np.isnan(positions_y))
        assert np.all(np.isfinite(positions_x))
        assert np.all(np.isfinite(positions_y))
    
    def test_get_cursor_velocity(self, loader):
        """Test getting cursor velocity via kinematics."""
        kinematics = loader.get_kinematics(start_time=1.0, end_time=1.1)
        
        assert isinstance(kinematics, dict)
        assert 'vx' in kinematics
        assert 'vy' in kinematics
        velocities_x = kinematics['vx']
        velocities_y = kinematics['vy']
        assert not np.any(np.isnan(velocities_x))
        assert not np.any(np.isnan(velocities_y))
        assert np.all(np.isfinite(velocities_x))
        assert np.all(np.isfinite(velocities_y))
    
    def test_get_trial_info(self, loader):
        """Test getting trial information."""
        trial_info = loader.get_trial_by_time(time=1.0)
        
        # May return None if no trial at that time
        if trial_info is not None:
            assert isinstance(trial_info, dict)
            # Should have at least start and stop times
            assert 'start_time' in trial_info
    
    def test_get_all_trials(self, loader):
        """Test getting all trials."""
        trials = loader.get_trials()
        
        assert isinstance(trials, list)
        assert len(trials) > 0
        
        # Check first trial structure
        trial = trials[0]
        assert 'start_time' in trial
        assert 'stop_time' in trial
        
        # Times should be valid
        assert trial['stop_time'] > trial['start_time']
    
    def test_get_trial_by_time(self, loader):
        """Test getting trial by time."""
        # Get first trial
        all_trials = loader.get_trials()
        if len(all_trials) == 0:
            pytest.skip("No trials in dataset")
        
        # Test getting trial at its start time
        first_trial = all_trials[0]
        trial = loader.get_trial_by_time(first_trial['start_time'] + 0.1)
        
        assert trial is not None
        assert trial['start_time'] == first_trial['start_time']
    
    def test_get_trials_by_target(self, loader):
        """Test filtering trials by target."""
        # Try to get trials for target 0
        trials = loader.get_trials_by_target(target_index=0)
        
        assert isinstance(trials, list)
        # If any trials exist, they should have the correct target
        for trial in trials:
            if 'active_target' in trial:
                assert trial['active_target'] == 0
    
    def test_time_out_of_bounds(self, loader):
        """Test behavior with out-of-bounds time values."""
        duration = loader.duration
        
        # Time before start - should return empty or zeros
        spike_counts = loader.get_binned_spikes(-1.0, -0.5, bin_size_ms=25.0)
        assert spike_counts.shape[1] == loader.num_channels
        
        # Time after end - should handle gracefully
        spike_counts = loader.get_binned_spikes(duration + 100.0, duration + 100.5, bin_size_ms=25.0)
        assert spike_counts.shape[1] == loader.num_channels
    
    def test_sequential_access(self, loader):
        """Test sequential data access pattern."""
        # Simulate streaming by accessing consecutive time windows
        times = [(0.0, 0.025), (0.025, 0.050), (0.050, 0.075), (0.075, 0.100)]
        
        for start, end in times:
            counts = loader.get_binned_spikes(start, end, bin_size_ms=25.0)
            assert counts.shape[1] == loader.num_channels
            kinematics = loader.get_kinematics(start, end)
            assert 'x' in kinematics
            assert 'y' in kinematics


class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_channel_ids_consistent(self, loader):
        """Test that number of channels is consistent across calls."""
        counts1 = loader.get_binned_spikes(1.0, 1.5, bin_size_ms=25.0)
        counts2 = loader.get_binned_spikes(2.0, 2.5, bin_size_ms=25.0)
        
        # Both should have same number of channels
        assert counts1.shape[1] == counts2.shape[1]
        assert counts1.shape[1] == loader.num_channels
    
    def test_num_channels_matches_spike_counts(self, loader):
        """Test that spike count dimensions match num_channels."""
        num_channels = loader.num_channels
        counts = loader.get_binned_spikes(1.0, 2.0, bin_size_ms=25.0)
        
        # Second dimension should be number of channels
        assert counts.shape[1] == num_channels


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
