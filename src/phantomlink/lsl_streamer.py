"""
LSL (Lab Streaming Layer) streaming module for PhantomLink.

This module implements LSL streaming alongside WebSocket for neural data distribution.
LSL provides precise timestamping and is widely used in neuroscience research.
"""
import logging
import asyncio
from typing import Optional, Dict, Any
import numpy as np

try:
    from pylsl import StreamInfo, StreamOutlet, local_clock
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False
    logging.warning("pylsl not available. LSL streaming will be disabled.")

from phantomlink.config import settings
from phantomlink.models import StreamPacket

logger = logging.getLogger(__name__)


class LSLStreamer:
    """
    LSL streaming manager for PhantomLink.
    
    Creates and manages LSL outlets for streaming neural data, kinematics,
    and intention data to LSL-compatible applications (e.g., OpenViBE, BCI2000).
    """
    
    def __init__(self, session_code: str = "default"):
        """
        Initialize LSL streamer.
        
        Args:
            session_code: Unique identifier for this streaming session
        """
        self.session_code = session_code
        self.neural_outlet: Optional[StreamOutlet] = None
        self.kinematics_outlet: Optional[StreamOutlet] = None
        self.intention_outlet: Optional[StreamOutlet] = None
        self.is_active = False
        self._packets_sent = 0
        
    def initialize(self, num_channels: int):
        """
        Initialize LSL outlets.
        
        Args:
            num_channels: Number of neural channels
        """
        if not LSL_AVAILABLE:
            logger.error("Cannot initialize LSL streamer: pylsl not available")
            return False
            
        if not settings.lsl_enabled:
            logger.info("LSL streaming is disabled in configuration")
            return False
        
        try:
            # Neural data stream (spike counts)
            neural_info = StreamInfo(
                name=f"{settings.lsl_stream_name}-Neural-{self.session_code}",
                type=settings.lsl_stream_type,
                channel_count=num_channels,
                nominal_srate=settings.stream_frequency_hz,
                channel_format='int32',
                source_id=f"{settings.lsl_source_id}-neural-{self.session_code}"
            )
            
            # Add channel metadata
            channels = neural_info.desc().append_child("channels")
            for i in range(num_channels):
                ch = channels.append_child("channel")
                ch.append_child_value("label", f"Ch{i}")
                ch.append_child_value("unit", "spikes")
                ch.append_child_value("type", "spike_count")
            
            self.neural_outlet = StreamOutlet(neural_info)
            logger.info(f"LSL Neural outlet created: {num_channels} channels at {settings.stream_frequency_hz}Hz")
            
            # Kinematics stream (vx, vy, x, y)
            kinematics_info = StreamInfo(
                name=f"{settings.lsl_stream_name}-Kinematics-{self.session_code}",
                type="Kinematics",
                channel_count=4,
                nominal_srate=settings.stream_frequency_hz,
                channel_format='float32',
                source_id=f"{settings.lsl_source_id}-kinematics-{self.session_code}"
            )
            
            # Add kinematics channel metadata
            kin_channels = kinematics_info.desc().append_child("channels")
            for label, unit in [("vx", "cm/s"), ("vy", "cm/s"), ("x", "cm"), ("y", "cm")]:
                ch = kin_channels.append_child("channel")
                ch.append_child_value("label", label)
                ch.append_child_value("unit", unit)
                ch.append_child_value("type", "position" if label in ["x", "y"] else "velocity")
            
            self.kinematics_outlet = StreamOutlet(kinematics_info)
            logger.info(f"LSL Kinematics outlet created")
            
            # Intention/Target stream (target_id, target_x, target_y, trial_id)
            intention_info = StreamInfo(
                name=f"{settings.lsl_stream_name}-Intention-{self.session_code}",
                type="Markers",
                channel_count=4,
                nominal_srate=settings.stream_frequency_hz,
                channel_format='float32',
                source_id=f"{settings.lsl_source_id}-intention-{self.session_code}"
            )
            
            # Add intention channel metadata
            int_channels = intention_info.desc().append_child("channels")
            for label in ["target_id", "target_x", "target_y", "trial_id"]:
                ch = int_channels.append_child("channel")
                ch.append_child_value("label", label)
                ch.append_child_value("type", "marker")
            
            self.intention_outlet = StreamOutlet(intention_info)
            logger.info(f"LSL Intention outlet created")
            
            self.is_active = True
            logger.info(f"LSL streaming initialized for session '{self.session_code}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LSL outlets: {e}")
            return False
    
    def push_packet(self, packet: StreamPacket):
        """
        Push a data packet to all LSL outlets.
        
        Args:
            packet: StreamPacket containing neural, kinematic, and intention data
        """
        if not self.is_active or not LSL_AVAILABLE:
            return
        
        try:
            # Get LSL timestamp (high precision)
            lsl_timestamp = local_clock()
            
            # Push neural data (spike counts)
            if self.neural_outlet and packet.spikes:
                neural_data = np.array(packet.spikes.spike_counts, dtype=np.int32)
                self.neural_outlet.push_sample(neural_data, timestamp=lsl_timestamp)
            
            # Push kinematics data
            if self.kinematics_outlet and packet.kinematics:
                kinematics_data = np.array([
                    packet.kinematics.vx,
                    packet.kinematics.vy,
                    packet.kinematics.x,
                    packet.kinematics.y
                ], dtype=np.float32)
                self.kinematics_outlet.push_sample(kinematics_data, timestamp=lsl_timestamp)
            
            # Push intention/target data
            if self.intention_outlet and packet.intention:
                intention_data = np.array([
                    float(packet.intention.target_id) if packet.intention.target_id is not None else -1.0,
                    packet.intention.target_x if packet.intention.target_x is not None else 0.0,
                    packet.intention.target_y if packet.intention.target_y is not None else 0.0,
                    float(packet.trial_id) if packet.trial_id is not None else -1.0
                ], dtype=np.float32)
                self.intention_outlet.push_sample(intention_data, timestamp=lsl_timestamp)
            
            self._packets_sent += 1
            
            # Log progress periodically
            if self._packets_sent % 1000 == 0:
                logger.debug(f"LSL: {self._packets_sent} packets sent")
                
        except Exception as e:
            logger.error(f"Error pushing LSL packet: {e}")
    
    async def push_packet_async(self, packet: StreamPacket):
        """
        Async wrapper for push_packet to avoid blocking.
        
        Args:
            packet: StreamPacket to push
        """
        # Run in thread pool to avoid blocking asyncio
        await asyncio.get_event_loop().run_in_executor(None, self.push_packet, packet)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get LSL streaming statistics.
        
        Returns:
            Dictionary with streaming stats
        """
        return {
            "is_active": self.is_active,
            "session_code": self.session_code,
            "packets_sent": self._packets_sent,
            "outlets": {
                "neural": self.neural_outlet is not None,
                "kinematics": self.kinematics_outlet is not None,
                "intention": self.intention_outlet is not None
            }
        }
    
    def cleanup(self):
        """Clean up LSL outlets."""
        if self.neural_outlet:
            del self.neural_outlet
            self.neural_outlet = None
        
        if self.kinematics_outlet:
            del self.kinematics_outlet
            self.kinematics_outlet = None
        
        if self.intention_outlet:
            del self.intention_outlet
            self.intention_outlet = None
        
        self.is_active = False
        logger.info(f"LSL streamer cleaned up for session '{self.session_code}'")


class LSLStreamManager:
    """
    Manager for multiple LSL streaming sessions.
    
    Manages LSL streamers for different sessions, similar to SessionManager.
    """
    
    def __init__(self):
        """Initialize the LSL stream manager."""
        self.streamers: Dict[str, LSLStreamer] = {}
        logger.info("LSL Stream Manager initialized")
    
    def create_streamer(self, session_code: str, num_channels: int) -> Optional[LSLStreamer]:
        """
        Create and initialize a new LSL streamer for a session.
        
        Args:
            session_code: Unique session identifier
            num_channels: Number of neural channels
            
        Returns:
            LSLStreamer instance or None if creation failed
        """
        if not LSL_AVAILABLE:
            logger.warning("LSL not available, cannot create streamer")
            return None
        
        if session_code in self.streamers:
            logger.warning(f"LSL streamer already exists for session '{session_code}'")
            return self.streamers[session_code]
        
        streamer = LSLStreamer(session_code)
        if streamer.initialize(num_channels):
            self.streamers[session_code] = streamer
            logger.info(f"Created LSL streamer for session '{session_code}'")
            return streamer
        else:
            logger.error(f"Failed to initialize LSL streamer for session '{session_code}'")
            return None
    
    def get_streamer(self, session_code: str) -> Optional[LSLStreamer]:
        """
        Get an existing LSL streamer.
        
        Args:
            session_code: Session identifier
            
        Returns:
            LSLStreamer instance or None if not found
        """
        return self.streamers.get(session_code)
    
    def remove_streamer(self, session_code: str) -> bool:
        """
        Remove and cleanup an LSL streamer.
        
        Args:
            session_code: Session identifier
            
        Returns:
            True if removed, False if not found
        """
        if session_code in self.streamers:
            self.streamers[session_code].cleanup()
            del self.streamers[session_code]
            logger.info(f"Removed LSL streamer for session '{session_code}'")
            return True
        return False
    
    def cleanup_all(self):
        """Clean up all LSL streamers."""
        for session_code in list(self.streamers.keys()):
            self.remove_streamer(session_code)
        logger.info("All LSL streamers cleaned up")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all LSL streamers.
        
        Returns:
            Dictionary with stats for each streamer
        """
        return {
            "total_streamers": len(self.streamers),
            "lsl_available": LSL_AVAILABLE,
            "lsl_enabled": settings.lsl_enabled,
            "streamers": {
                code: streamer.get_stats() 
                for code, streamer in self.streamers.items()
            }
        }
