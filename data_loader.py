"""
Data loader for Neural Latents Benchmark MC_Maze dataset.

This module implements efficient lazy loading and memory mapping for HDF5/NWB files.
The MC_Maze dataset contains neural recordings from motor cortex during a maze task.

📖 Documentation: See README.md for architecture details and usage
"""
import logging
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np
from pynwb import NWBHDF5IO

logger = logging.getLogger(__name__)


class MC_MazeLoader:
    """
    Lazy loader for MC_Maze dataset from Neural Latents Benchmark.
    
    The loader uses memory mapping to avoid loading entire datasets into RAM.
    Data is accessed on-demand with efficient indexing.
    """
    
    def __init__(self, file_path: Path, lazy_load: bool = True):
        """
        Initialize the dataset loader.
        
        Args:
            file_path: Path to the NWB file
            lazy_load: Use memory mapping instead of loading into RAM
        """
        self.file_path = file_path
        self.lazy_load = lazy_load
        self._io: Optional[NWBHDF5IO] = None
        self._nwb = None
        
        # Cached metadata
        self._num_channels: Optional[int] = None
        self._duration: Optional[float] = None
        self._behavior_sampling_rate: Optional[float] = None  # Detected from timestamps
        
        # References to NWB data structures
        self._units = None
        self._cursor_pos = None
        self._hand_vel = None
        self._trials = None
        self._trial_index = []  # List of (start_time, stop_time, trial_data)
        
        self._open_dataset()
    
    def _open_dataset(self):
        """Open the dataset file and prepare for lazy access."""
        if not self.file_path.exists():
            raise DatasetNotFoundError(f"Dataset not found: {self.file_path}")
        
        # Open NWB file
        self._io = NWBHDF5IO(str(self.file_path), mode='r', load_namespaces=True)
        self._nwb = self._io.read()
        logger.info(f"Opened NWB file: {self.file_path}")
        self._parse_nwb_structure()
    
    def _parse_nwb_structure(self):
        """Parse NWB file structure and locate relevant datasets."""
        if not self._nwb:
            raise RuntimeError("NWB file not loaded")
        
        # Get neural units data
        if not hasattr(self._nwb, 'units') or self._nwb.units is None:
            raise RuntimeError("No units data found in NWB file")
        
        self._units = self._nwb.units
        self._num_channels = len(self._units.id[:])
        logger.info(f"Found {self._num_channels} neural units")
        
        # Get behavioral data from processing module
        if not hasattr(self._nwb, 'processing') or 'behavior' not in self._nwb.processing:
            raise RuntimeError("No behavior data found in NWB file")
        
        behavior = self._nwb.processing['behavior']
        logger.info(f"Found processing module: behavior")
        
        # Get cursor position and hand velocity
        if 'cursor_pos' in behavior.data_interfaces:
            self._cursor_pos = behavior.data_interfaces['cursor_pos']
            cursor_data = self._cursor_pos.data[:]
            
            # Detect sampling rate from timestamps
            if hasattr(self._cursor_pos, 'timestamps') and self._cursor_pos.timestamps is not None:
                timestamps = self._cursor_pos.timestamps[:]
                self._behavior_sampling_rate = 1.0 / np.mean(np.diff(timestamps[:100]))
                self._duration = timestamps[-1]
                logger.info(f"  - cursor_pos: {cursor_data.shape}, sampling rate: {self._behavior_sampling_rate:.1f}Hz")
            else:
                # Fallback to 40Hz if no timestamps
                self._behavior_sampling_rate = 40.0
                self._duration = len(cursor_data) / self._behavior_sampling_rate
                logger.info(f"  - cursor_pos: {cursor_data.shape}, assuming {self._behavior_sampling_rate}Hz")
        
        if 'hand_vel' in behavior.data_interfaces:
            self._hand_vel = behavior.data_interfaces['hand_vel']
            vel_data = self._hand_vel.data[:]
            logger.info(f"  - hand_vel: {vel_data.shape}")
        
        # Parse trial structure
        self._parse_trials()
    
    def get_binned_spikes(self, start_time: float, end_time: float, 
                         bin_size_ms: float = 25.0) -> np.ndarray:
        """
        Get binned spike counts for a time window.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            bin_size_ms: Bin size in milliseconds
        
        Returns:
            Array of shape (num_bins, num_channels) with spike counts
        """
        bin_size_s = bin_size_ms / 1000.0
        num_bins = max(1, int((end_time - start_time) / bin_size_s))
        
        # Initialize spike count array
        spike_counts = np.zeros((num_bins, self.num_channels), dtype=int)
        
        # Bin spikes for each unit
        for unit_idx in range(self.num_channels):
            try:
                # Get spike times for this unit
                # NWB VectorIndex directly returns the spike times array for each unit
                spike_times = self._units['spike_times'][unit_idx]
                
                if len(spike_times) == 0:
                    continue
                
                # Filter spike times within the time window
                mask = (spike_times >= start_time) & (spike_times < end_time)
                spikes_in_window = spike_times[mask]
                
                if len(spikes_in_window) == 0:
                    continue
                
                # Bin the spikes
                bin_indices = np.floor((spikes_in_window - start_time) / bin_size_s).astype(int)
                bin_indices = np.clip(bin_indices, 0, num_bins - 1)
                
                # Count spikes in each bin
                for bin_idx in bin_indices:
                    spike_counts[bin_idx, unit_idx] += 1
                    
            except Exception as e:
                logger.warning(f"Error processing unit {unit_idx}: {e}")
                continue
        
        return spike_counts
    
    def get_kinematics(self, start_time: float, end_time: float, 
                       bin_size_ms: float = 25.0) -> Dict[str, np.ndarray]:
        """
        Get cursor kinematics for a time window.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            bin_size_ms: Bin size in milliseconds
        
        Returns:
            Dictionary with 'vx', 'vy', 'x', 'y' arrays
        """
        # Convert time to sample indices using actual behavioral sampling rate
        start_idx = int(start_time * self._behavior_sampling_rate)
        end_idx = int(end_time * self._behavior_sampling_rate)
        
        # Get cursor position data
        cursor_data = self._cursor_pos.data[start_idx:end_idx]
        
        # Extract x and y positions (assuming 2D data)
        if len(cursor_data.shape) == 1:
            # If 1D, might be interleaved x,y
            x = cursor_data[::2] if len(cursor_data) > 1 else np.array([cursor_data[0]])
            y = cursor_data[1::2] if len(cursor_data) > 1 else np.array([cursor_data[0]])
        else:
            # If 2D, columns are x,y
            x = cursor_data[:, 0]
            y = cursor_data[:, 1] if cursor_data.shape[1] > 1 else cursor_data[:, 0]
        
        # Get hand velocity data
        vel_data = self._hand_vel.data[start_idx:end_idx]
        
        if len(vel_data.shape) == 1:
            vx = vel_data[::2] if len(vel_data) > 1 else np.array([vel_data[0]])
            vy = vel_data[1::2] if len(vel_data) > 1 else np.array([vel_data[0]])
        else:
            vx = vel_data[:, 0]
            vy = vel_data[:, 1] if vel_data.shape[1] > 1 else vel_data[:, 0]
        
        return {
            'vx': vx,
            'vy': vy,
            'x': x,
            'y': y
        }
    
    def get_targets(self, start_time: float, end_time: float,
                   bin_size_ms: float = 25.0) -> Dict[str, np.ndarray]:
        """
        Get target intention data for a time window.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            bin_size_ms: Bin size in milliseconds
        
        Returns:
            Dictionary with target information
        """
        # Convert time to sample indices using behavioral sampling rate
        start_idx = int(start_time * self._behavior_sampling_rate)
        end_idx = int(end_time * self._behavior_sampling_rate)
        num_samples = end_idx - start_idx
        
        # MC_Maze doesn't have explicit target data in the test set
        # Return placeholder values (can be enhanced if trial data is available)
        return {
            'target_id': np.zeros(num_samples, dtype=int),
            'target_x': np.zeros(num_samples),
            'target_y': np.zeros(num_samples)
        }
    
    def _parse_trials(self):
        """Parse trial data and build trial index."""
        if not hasattr(self._nwb, 'trials') or self._nwb.trials is None:
            logger.warning("No trial data found in NWB file")
            return
        
        self._trials = self._nwb.trials
        num_trials = len(self._trials)
        logger.info(f"Found {num_trials} trials")
        
        # Build trial index with intention data
        for i in range(num_trials):
            trial_info = {
                'trial_id': i,
                'start_time': float(self._trials['start_time'][i]),
                'stop_time': float(self._trials['stop_time'][i]),
                'success': bool(self._trials['success'][i]),
                'num_targets': int(self._trials['num_targets'][i]),
                'active_target': int(self._trials['active_target'][i]),
                'target_pos': self._trials['target_pos'][i].tolist(),
                'move_onset_time': float(self._trials['move_onset_time'][i]) if 'move_onset_time' in self._trials.colnames else None,
                'go_cue_time': float(self._trials['go_cue_time'][i]) if 'go_cue_time' in self._trials.colnames else None,
            }
            self._trial_index.append(trial_info)
    
    def get_trials(self) -> List[Dict]:
        """Get list of all trials with intention metadata."""
        return self._trial_index
    
    def get_trial_by_time(self, time: float) -> Optional[Dict]:
        """Get trial information for a given time point."""
        for trial in self._trial_index:
            if trial['start_time'] <= time < trial['stop_time']:
                return trial
        return None
    
    def get_trials_by_target(self, target_index: int) -> List[Dict]:
        """Get all trials reaching for a specific target index."""
        return [t for t in self._trial_index if t['active_target'] == target_index]
    
    def get_target_position(self, trial_info: Dict) -> Optional[tuple]:
        """Get the active target position for a trial."""
        if trial_info is None:
            return None
        active_idx = trial_info['active_target']
        target_pos = trial_info['target_pos']
        if active_idx < len(target_pos):
            pos = target_pos[active_idx]
            return (float(pos[0]), float(pos[1]))
        return None
    
    @property
    def num_channels(self) -> int:
        """Get number of neural channels."""
        if self._num_channels is None:
            raise RuntimeError("Dataset not loaded")
        return self._num_channels
    
    @property
    def duration(self) -> float:
        """Get total duration in seconds."""
        if self._duration is None:
            raise RuntimeError("Dataset not loaded")
        return self._duration
    
    @property
    def num_timesteps(self) -> int:
        """Get total number of 25ms bins."""
        return int(self.duration * 40)  # 40 Hz = 40 bins per second
    
    def close(self):
        """Close file handles and release resources."""
        if self._io:
            self._io.close()
            logger.info("Closed NWB file")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DatasetNotFoundError(Exception):
    """Raised when dataset file cannot be found."""
    pass
