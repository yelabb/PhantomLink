"""
PhantomLink - Real-Time Neural Data Streaming Server for BCI Development.

The Ethereal/Mailtrap for Neurotechnology
"""
__version__ = "0.2.0"
__author__ = "PhantomLink Contributors"
__description__ = "Real-Time Neural Data Streaming Server for BCI Development"

from phantomlink.config import settings
from phantomlink.models import (
    StreamPacket,
    StreamMetadata,
    SpikeData,
    Kinematics,
    TargetIntention
)
from phantomlink.data_loader import MC_MazeLoader
from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware
from phantomlink.session_manager import SessionManager

__all__ = [
    "settings",
    "StreamPacket",
    "StreamMetadata",
    "SpikeData",
    "Kinematics",
    "TargetIntention",
    "MC_MazeLoader",
    "PlaybackEngine",
    "NoiseInjectionMiddleware",
    "SessionManager"
]
