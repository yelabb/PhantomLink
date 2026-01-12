"""
Test LSL streaming functionality.
"""
import pytest
import asyncio
import time
from pathlib import Path

try:
    from pylsl import StreamInlet, resolve_stream
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False

from phantomlink.lsl_streamer import LSLStreamer, LSLStreamManager
from phantomlink.models import StreamPacket, SpikeData, Kinematics, TargetIntention
from phantomlink.config import settings


@pytest.fixture
def sample_packet():
    """Create a sample stream packet for testing."""
    return StreamPacket(
        timestamp=time.time(),
        sequence_number=1,
        spikes=SpikeData(
            channel_ids=list(range(10)),
            spike_counts=[2, 0, 1, 3, 0, 1, 0, 2, 1, 0],
            bin_size_ms=25
        ),
        kinematics=Kinematics(
            vx=15.2,
            vy=-8.4,
            x=125.3,
            y=-78.9
        ),
        intention=TargetIntention(
            target_id=0,
            target_x=-77.0,
            target_y=0.0
        ),
        trial_id=42,
        trial_time_ms=1050.0
    )


@pytest.mark.skipif(not LSL_AVAILABLE, reason="pylsl not installed")
class TestLSLStreamer:
    """Test LSL streaming functionality."""
    
    def test_lsl_streamer_initialization(self):
        """Test LSL streamer can be initialized."""
        streamer = LSLStreamer(session_code="test-session")
        assert streamer.session_code == "test-session"
        assert not streamer.is_active
        assert streamer._packets_sent == 0
    
    def test_lsl_streamer_initialize_outlets(self):
        """Test LSL outlet creation."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        streamer = LSLStreamer(session_code="test-session")
        success = streamer.initialize(num_channels=10)
        
        if success:
            assert streamer.is_active
            assert streamer.neural_outlet is not None
            assert streamer.kinematics_outlet is not None
            assert streamer.intention_outlet is not None
            
            # Cleanup
            streamer.cleanup()
            assert not streamer.is_active
    
    def test_lsl_push_packet(self, sample_packet):
        """Test pushing a packet through LSL."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        streamer = LSLStreamer(session_code="test-push")
        success = streamer.initialize(num_channels=10)
        
        if success:
            # Push packet
            streamer.push_packet(sample_packet)
            assert streamer._packets_sent == 1
            
            # Push more packets
            for i in range(10):
                streamer.push_packet(sample_packet)
            assert streamer._packets_sent == 11
            
            # Cleanup
            streamer.cleanup()
    
    @pytest.mark.asyncio
    async def test_lsl_push_packet_async(self, sample_packet):
        """Test async packet pushing."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        streamer = LSLStreamer(session_code="test-async")
        success = streamer.initialize(num_channels=10)
        
        if success:
            # Push packet asynchronously
            await streamer.push_packet_async(sample_packet)
            assert streamer._packets_sent == 1
            
            # Cleanup
            streamer.cleanup()
    
    def test_lsl_streamer_stats(self, sample_packet):
        """Test getting streamer statistics."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        streamer = LSLStreamer(session_code="test-stats")
        streamer.initialize(num_channels=10)
        
        stats = streamer.get_stats()
        assert "is_active" in stats
        assert "session_code" in stats
        assert "packets_sent" in stats
        assert "outlets" in stats
        assert stats["session_code"] == "test-stats"
        
        streamer.cleanup()


@pytest.mark.skipif(not LSL_AVAILABLE, reason="pylsl not installed")
class TestLSLStreamManager:
    """Test LSL stream manager."""
    
    def test_manager_initialization(self):
        """Test stream manager initialization."""
        manager = LSLStreamManager()
        assert len(manager.streamers) == 0
    
    def test_create_streamer(self):
        """Test creating a streamer through manager."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        manager = LSLStreamManager()
        streamer = manager.create_streamer("test-session-1", num_channels=10)
        
        if streamer:
            assert "test-session-1" in manager.streamers
            assert streamer.is_active
            
            # Cleanup
            manager.cleanup_all()
    
    def test_get_streamer(self):
        """Test retrieving a streamer."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        manager = LSLStreamManager()
        streamer1 = manager.create_streamer("test-session-2", num_channels=10)
        
        if streamer1:
            # Get existing streamer
            streamer2 = manager.get_streamer("test-session-2")
            assert streamer2 is streamer1
            
            # Get non-existent streamer
            streamer3 = manager.get_streamer("nonexistent")
            assert streamer3 is None
            
            # Cleanup
            manager.cleanup_all()
    
    def test_remove_streamer(self):
        """Test removing a streamer."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        manager = LSLStreamManager()
        streamer = manager.create_streamer("test-session-3", num_channels=10)
        
        if streamer:
            assert "test-session-3" in manager.streamers
            
            # Remove streamer
            success = manager.remove_streamer("test-session-3")
            assert success
            assert "test-session-3" not in manager.streamers
            
            # Try removing again
            success = manager.remove_streamer("test-session-3")
            assert not success
    
    def test_manager_stats(self):
        """Test getting manager statistics."""
        manager = LSLStreamManager()
        
        stats = manager.get_stats()
        assert "total_streamers" in stats
        assert "lsl_available" in stats
        assert "lsl_enabled" in stats
        assert "streamers" in stats
        assert stats["total_streamers"] == 0
        
        manager.cleanup_all()
    
    def test_cleanup_all(self):
        """Test cleaning up all streamers."""
        if not settings.lsl_enabled:
            pytest.skip("LSL disabled in config")
        
        manager = LSLStreamManager()
        
        # Create multiple streamers
        for i in range(3):
            manager.create_streamer(f"test-session-{i}", num_channels=10)
        
        # Cleanup all
        manager.cleanup_all()
        assert len(manager.streamers) == 0


@pytest.mark.skipif(not LSL_AVAILABLE, reason="pylsl not installed")
@pytest.mark.integration
def test_lsl_stream_reception(sample_packet):
    """Integration test: Create LSL stream and verify reception."""
    if not settings.lsl_enabled:
        pytest.skip("LSL disabled in config")
    
    # Create streamer
    streamer = LSLStreamer(session_code="test-reception")
    success = streamer.initialize(num_channels=10)
    
    if not success:
        pytest.skip("Could not initialize LSL streamer")
    
    try:
        # Push some packets
        for i in range(5):
            streamer.push_packet(sample_packet)
            time.sleep(0.025)  # 40Hz
        
        # Try to resolve the stream
        streams = resolve_stream('type', 'EEG', timeout=2.0)
        
        # Look for our stream
        found = False
        for stream in streams:
            if "test-reception" in stream.name():
                found = True
                assert stream.channel_count() == 10
                assert stream.nominal_srate() == 40
                break
        
        assert found, "Stream not found by LSL resolver"
        
    finally:
        streamer.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
