"""
PhantomLink Core - BCI Mock Server

The Ethereal/Mailtrap for Neurotechnology Development
"""

__version__ = "0.1.0"
__author__ = "PhantomLink Contributors"
__description__ = "BCI Mock Server for streaming pre-recorded neural data"

from .config import settings
from .models import StreamPacket, SpikeData, Kinematics, TargetIntention
from .data_loader import MC_MazeLoader
from .playback_engine import PlaybackEngine

__all__ = [
    "settings",
    "StreamPacket",
    "SpikeData", 
    "Kinematics",
    "TargetIntention",
    "MC_MazeLoader",
    "PlaybackEngine",
]
