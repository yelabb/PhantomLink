"""
Playback engine for streaming neural data at 40Hz with strict timing.

This module implements the core streaming logic with precise time-alignment
between neural spikes and behavioral ground truth.

📖 Documentation: See README.md for architecture details and performance specs
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, AsyncGenerator
import numpy as np

from config import settings
from models import StreamPacket, SpikeData, Kinematics, TargetIntention, StreamMetadata
from data_loader import MC_MazeLoader

logger = logging.getLogger(__name__)


class PlaybackEngine:
    """
    40Hz playback engine with strict timing guarantees.
    
    The engine maintains a steady 25ms update rate, streaming time-aligned
    neural and behavioral data. It uses asyncio for non-blocking operation
    and precise timing control.
    """
    
    def __init__(self, data_path: Path):
        """
        Initialize the playback engine.
        
        Args:
            data_path: Path to the dataset file
        """
        self.data_path = data_path
        self.loader: Optional[MC_MazeLoader] = None
        self.is_running = False
        self.is_paused = False
        
        # Playback state
        self._current_index = 0
        self._sequence_number = 0
        self._start_time: Optional[float] = None
        
        # Performance metrics
        self._packets_sent = 0
        self._timing_errors = []
        
    async def initialize(self):
        """Initialize the data loader and prepare for streaming."""
        logger.info(f"Initializing playback engine with dataset: {self.data_path}")
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}. Please provide a valid NWB file.")
        
        self.loader = MC_MazeLoader(self.data_path)
        logger.info(f"Dataset loaded: {self.loader.num_channels} channels, "
                   f"{self.loader.duration:.1f}s duration, "
                   f"{self.loader.num_timesteps} timesteps")
    
    def get_metadata(self) -> StreamMetadata:
        """Get metadata about the stream."""
        if not self.loader:
            raise RuntimeError("Playback engine not initialized")
        
        return StreamMetadata(
            dataset="MC_Maze",
            total_packets=self.loader.num_timesteps,
            frequency_hz=settings.stream_frequency_hz,
            num_channels=self.loader.num_channels,
            duration_seconds=self.loader.duration,
            num_trials=len(self.loader.get_trials())
        )
    
    async def stream(self, loop: bool = True, trial_filter: Optional[int] = None, 
                    target_filter: Optional[int] = None) -> AsyncGenerator[StreamPacket, None]:
        """
        Stream packets at 40Hz with strict timing.
        
        Args:
            loop: Whether to loop the dataset when it ends
            trial_filter: If set, only stream packets from this trial_id
            target_filter: If set, only stream packets reaching for this target index
        
        Yields:
            StreamPacket objects at 25ms intervals
        """
        if not self.loader:
            await self.initialize()
        
        self.is_running = True
        self._start_time = time.time()
        self._current_index = 0
        self._sequence_number = 0
        
        logger.info("Starting 40Hz playback stream")
        
        # Calculate precise interval in seconds
        interval = settings.packet_interval_ms / 1000.0  # 0.025s
        
        while self.is_running:
            if self.is_paused:
                await asyncio.sleep(0.1)
                continue
            
            # Record expected timestamp for this packet
            expected_time = self._start_time + (self._sequence_number * interval)
            
            # Generate packet
            packet = await self._generate_packet()
            
            if packet is None:
                # Reached end of dataset
                if loop:
                    logger.info("Reached end of dataset, looping...")
                    self._current_index = 0
                    continue
                else:
                    logger.info("Reached end of dataset, stopping stream")
                    break
            
            # Apply filters if specified
            if trial_filter is not None and packet.trial_id != trial_filter:
                self._current_index += 1
                continue
            
            if target_filter is not None and packet.intention.target_id != target_filter:
                self._current_index += 1
                continue
            
            yield packet
            
            self._packets_sent += 1
            self._sequence_number += 1
            
            # Calculate timing error and adjust
            current_time = time.time()
            timing_error = current_time - expected_time
            self._timing_errors.append(timing_error)
            
            # Sleep until next packet is due
            next_packet_time = self._start_time + (self._sequence_number * interval)
            sleep_duration = next_packet_time - time.time()
            
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)
            else:
                # We're running behind schedule
                if abs(sleep_duration) > interval * 0.5:
                    logger.warning(f"Timing slip: {sleep_duration*1000:.2f}ms behind schedule")
            
            # Log performance every 1000 packets (25 seconds)
            if self._packets_sent % 1000 == 0:
                avg_error = np.mean(self._timing_errors[-1000:]) * 1000
                std_error = np.std(self._timing_errors[-1000:]) * 1000
                logger.info(f"Performance: {self._packets_sent} packets, "
                          f"timing error: {avg_error:.3f}±{std_error:.3f}ms")
        
        self.is_running = False
        logger.info(f"Playback stopped. Total packets sent: {self._packets_sent}")
    
    async def _generate_packet(self) -> Optional[StreamPacket]:
        """
        Generate a single packet with time-aligned data.
        
        Returns:
            StreamPacket or None if end of dataset reached
        """
        if not self.loader:
            return None
        
        # Check if we've reached the end
        if self._current_index >= self.loader.num_timesteps:
            return None
        
        # Calculate time window for this bin
        bin_size_s = settings.packet_interval_ms / 1000.0
        start_time = self._current_index * bin_size_s
        end_time = start_time + bin_size_s
        
        # Get neural data
        spike_counts_array = self.loader.get_binned_spikes(
            start_time, end_time, bin_size_ms=settings.packet_interval_ms
        )
        
        # Get kinematics data
        kinematics_data = self.loader.get_kinematics(
            start_time, end_time, bin_size_ms=settings.packet_interval_ms
        )
        
        # Get target data
        target_data = self.loader.get_targets(
            start_time, end_time, bin_size_ms=settings.packet_interval_ms
        )
        
        # Get trial context for this time point
        trial_info = self.loader.get_trial_by_time(start_time)
        trial_id = trial_info['trial_id'] if trial_info else None
        
        # Get actual target position if in trial
        target_pos = None
        if trial_info:
            target_pos = self.loader.get_target_position(trial_info)
        
        # Extract single time bin (first bin of the returned arrays)
        spike_counts = spike_counts_array[0] if len(spike_counts_array) > 0 else np.zeros(self.loader.num_channels)
        
        # Create packet
        packet = StreamPacket(
            timestamp=time.time(),
            sequence_number=self._sequence_number,
            spikes=SpikeData(
                channel_ids=list(range(self.loader.num_channels)),
                spike_counts=spike_counts.astype(int).tolist(),
                bin_size_ms=settings.packet_interval_ms
            ),
            kinematics=Kinematics(
                vx=float(kinematics_data['vx'][0]),
                vy=float(kinematics_data['vy'][0]),
                x=float(kinematics_data['x'][0]),
                y=float(kinematics_data['y'][0])
            ),
            intention=TargetIntention(
                target_id=trial_info['active_target'] if trial_info else None,
                target_x=float(target_pos[0]) if target_pos else None,
                target_y=float(target_pos[1]) if target_pos else None
            ),
            trial_id=trial_id,
            trial_time_ms=start_time * 1000.0
        )
        
        self._current_index += 1
        return packet
    
    def pause(self):
        """Pause the playback."""
        self.is_paused = True
        logger.info("Playback paused")
    
    def resume(self):
        """Resume the playback."""
        self.is_paused = False
        logger.info("Playback resumed")
    
    def stop(self):
        """Stop the playback."""
        self.is_running = False
        logger.info("Playback stopped")
    
    def seek(self, position_seconds: float):
        """
        Seek to a specific position in the dataset.
        
        Args:
            position_seconds: Target position in seconds
        """
        if not self.loader:
            return
        
        # Convert seconds to bin index
        self._current_index = int(position_seconds * settings.stream_frequency_hz)
        self._current_index = max(0, min(self._current_index, self.loader.num_timesteps - 1))
        
        logger.info(f"Seeked to {position_seconds:.2f}s (index {self._current_index})")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.loader:
            self.loader.close()
        logger.info("Playback engine cleaned up")
    
    def get_stats(self) -> dict:
        """Get playback statistics."""
        if not self._timing_errors:
            return {}
        
        recent_errors = self._timing_errors[-1000:] if len(self._timing_errors) > 1000 else self._timing_errors
        
        return {
            'packets_sent': self._packets_sent,
            'current_index': self._current_index,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'timing_error_mean_ms': float(np.mean(recent_errors) * 1000),
            'timing_error_std_ms': float(np.std(recent_errors) * 1000),
            'timing_error_max_ms': float(np.max(np.abs(recent_errors)) * 1000)
        }
