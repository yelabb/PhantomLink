"""
Data models for PhantomLink streaming protocol.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SpikeData(BaseModel):
    """Binned spike counts for the channel array."""
    
    channel_ids: List[int] = Field(description="Array of channel identifiers")
    spike_counts: List[int] = Field(description="Binned spike counts per channel")
    bin_size_ms: float = Field(default=25.0, description="Bin size in milliseconds")


class Kinematics(BaseModel):
    """Cursor kinematics ground truth."""
    
    vx: float = Field(description="X-axis velocity")
    vy: float = Field(description="Y-axis velocity")
    x: Optional[float] = Field(default=None, description="X position")
    y: Optional[float] = Field(default=None, description="Y position")


class TargetIntention(BaseModel):
    """Target intention ground truth."""
    
    target_id: Optional[int] = Field(default=None, description="Current target identifier")
    target_x: Optional[float] = Field(default=None, description="Target X position")
    target_y: Optional[float] = Field(default=None, description="Target Y position")
    distance_to_target: Optional[float] = Field(default=None, description="Distance to target")


class StreamPacket(BaseModel):
    """Complete data packet for 40Hz streaming."""
    
    timestamp: float = Field(description="Unix timestamp in seconds")
    sequence_number: int = Field(description="Monotonic packet sequence number")
    
    # Input: Neural data
    spikes: SpikeData = Field(description="Spike counts for all channels")
    
    # Ground Truth: Behavioral data
    kinematics: Kinematics = Field(description="Cursor kinematics")
    intention: TargetIntention = Field(description="Target intention")
    
    # Metadata
    trial_id: Optional[int] = Field(default=None, description="Trial identifier")
    trial_time_ms: Optional[float] = Field(default=None, description="Time within trial")


class StreamMetadata(BaseModel):
    """Metadata about the stream."""
    
    dataset: str = Field(description="Dataset name")
    total_packets: int = Field(description="Total number of packets in dataset")
    frequency_hz: int = Field(description="Stream frequency in Hz")
    num_channels: int = Field(description="Number of neural channels")
    duration_seconds: float = Field(description="Total duration of dataset")
    num_trials: int = Field(description="Number of trials in dataset")
