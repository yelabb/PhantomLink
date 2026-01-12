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
        assert loader._io is None  # Not loaded yet
    
    def test_open_close(self, loader):
        """Test opening and closing the dataset."""
        loader.open()
        assert loader._io is not None
        assert loader._nwb is not None
        
        loader.close()
        assert loader._io is None
        assert loader._nwb is None
    
    def test_context_manager(self):
        """Test using loader as context manager."""
        if not DATA_PATH.exists():
            pytest.skip(f"Test data not found at {DATA_PATH}")
        
        with MC_MazeLoader(DATA_PATH) as loader:
            assert loader._io is not None
            loader.open()  # Should be idempotent
        
        # After exiting context, should be closed
        assert loader._io is None
    
    def test_get_num_channels(self, loader):
        """Test getting number of channels."""
        loader.open()
        num_channels = loader.get_num_channels()
        assert isinstance(num_channels, int)
        assert num_channels > 0
        loader.close()
    
    def test_get_duration(self, loader):
        """Test getting dataset duration."""
        loader.open()
        duration = loader.get_duration()
        assert isinstance(duration, float)
        assert duration > 0
        loader.close()
    
    def test_get_behavior_sampling_rate(self, loader):
        """Test detecting behavior sampling rate."""
        loader.open()
        rate = loader.get_behavior_sampling_rate()
        assert isinstance(rate, float)
        assert rate > 0
        # Should be around 40-50 Hz for typical recordings
        assert 10 < rate < 200
        loader.close()
    
    def test_get_spike_counts_at_time(self, loader):
        """Test getting spike counts at specific time."""
        loader.open()
        
        # Get spike counts at t=1.0s
        spike_counts, channel_ids = loader.get_spike_counts_at_time(
            time_s=1.0,
            bin_size_ms=25.0
        )
        
        assert isinstance(spike_counts, np.ndarray)
        assert isinstance(channel_ids, np.ndarray)
        assert len(spike_counts) == len(channel_ids)
        assert len(spike_counts) == loader.get_num_channels()
        
        # Spike counts should be non-negative integers
        assert np.all(spike_counts >= 0)
        assert spike_counts.dtype == np.int32
        
        loader.close()
    
    def test_get_spike_counts_different_bin_sizes(self, loader):
        """Test spike counts with different bin sizes."""
        loader.open()
        
        counts_25ms, _ = loader.get_spike_counts_at_time(1.0, bin_size_ms=25.0)
        counts_50ms, _ = loader.get_spike_counts_at_time(1.0, bin_size_ms=50.0)
        
        # Larger bin should generally have more spikes
        assert counts_50ms.sum() >= counts_25ms.sum()
        
        loader.close()
    
    def test_get_cursor_position(self, loader):
        """Test getting cursor position."""
        loader.open()
        
        x, y = loader.get_cursor_position(time_s=1.0)
        
        assert isinstance(x, float)
        assert isinstance(y, float)
        # Positions should be reasonable (not NaN or infinite)
        assert not np.isnan(x)
        assert not np.isnan(y)
        assert np.isfinite(x)
        assert np.isfinite(y)
        
        loader.close()
    
    def test_get_cursor_velocity(self, loader):
        """Test getting cursor velocity."""
        loader.open()
        
        vx, vy = loader.get_cursor_velocity(time_s=1.0)
        
        assert isinstance(vx, float)
        assert isinstance(vy, float)
        assert not np.isnan(vx)
        assert not np.isnan(vy)
        assert np.isfinite(vx)
        assert np.isfinite(vy)
        
        loader.close()
    
    def test_get_trial_info(self, loader):
        """Test getting trial information."""
        loader.open()
        
        trial_info = loader.get_trial_info(time_s=1.0)
        
        assert isinstance(trial_info, dict)
        # Should have at least trial_id
        assert 'trial_id' in trial_info
        
        loader.close()
    
    def test_get_all_trials(self, loader):
        """Test getting all trials."""
        loader.open()
        
        trials = loader.get_all_trials()
        
        assert isinstance(trials, list)
        assert len(trials) > 0
        
        # Check first trial structure
        trial = trials[0]
        assert 'trial_id' in trial
        assert 'start_time' in trial
        assert 'stop_time' in trial
        
        # Times should be valid
        assert trial['stop_time'] > trial['start_time']
        
        loader.close()
    
    def test_get_trial_by_id(self, loader):
        """Test getting specific trial by ID."""
        loader.open()
        
        # Get first trial
        all_trials = loader.get_all_trials()
        if len(all_trials) == 0:
            pytest.skip("No trials in dataset")
        
        first_trial_id = all_trials[0]['trial_id']
        trial = loader.get_trial_by_id(first_trial_id)
        
        assert trial is not None
        assert trial['trial_id'] == first_trial_id
        
        loader.close()
    
    def test_get_trials_by_target(self, loader):
        """Test filtering trials by target."""
        loader.open()
        
        # Try to get trials for target 0
        trials = loader.get_trials_by_target(target_index=0)
        
        assert isinstance(trials, list)
        # If any trials exist, they should have the correct target
        for trial in trials:
            if 'active_target' in trial:
                assert trial['active_target'] == 0
        
        loader.close()
    
    def test_time_out_of_bounds(self, loader):
        """Test behavior with out-of-bounds time values."""
        loader.open()
        
        duration = loader.get_duration()
        
        # Time before start
        spike_counts, _ = loader.get_spike_counts_at_time(-1.0, bin_size_ms=25.0)
        assert len(spike_counts) > 0  # Should handle gracefully
        
        # Time after end
        spike_counts, _ = loader.get_spike_counts_at_time(duration + 100.0, bin_size_ms=25.0)
        assert len(spike_counts) > 0  # Should handle gracefully
        
        loader.close()
    
    def test_sequential_access(self, loader):
        """Test sequential data access pattern."""
        loader.open()
        
        # Simulate streaming by accessing consecutive time points
        times = [0.0, 0.025, 0.050, 0.075, 0.100]
        
        for t in times:
            counts, _ = loader.get_spike_counts_at_time(t, bin_size_ms=25.0)
            assert len(counts) > 0
            x, y = loader.get_cursor_position(t)
            assert not np.isnan(x)
        
        loader.close()


class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_channel_ids_consistent(self, loader):
        """Test that channel IDs are consistent across calls."""
        loader.open()
        
        _, ids1 = loader.get_spike_counts_at_time(1.0, bin_size_ms=25.0)
        _, ids2 = loader.get_spike_counts_at_time(2.0, bin_size_ms=25.0)
        
        assert np.array_equal(ids1, ids2)
        
        loader.close()
    
    def test_num_channels_matches_spike_counts(self, loader):
        """Test that spike count length matches num_channels."""
        loader.open()
        
        num_channels = loader.get_num_channels()
        counts, ids = loader.get_spike_counts_at_time(1.0, bin_size_ms=25.0)
        
        assert len(counts) == num_channels
        assert len(ids) == num_channels
        
        loader.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
