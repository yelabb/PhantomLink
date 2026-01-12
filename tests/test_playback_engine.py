"""
Unit tests for playback engine (playback_engine.py).

Tests streaming logic, timing accuracy, and state management.
"""
import pytest
import asyncio
import time
from pathlib import Path
from phantomlink.playback_engine import PlaybackEngine
from phantomlink.models import StreamPacket


DATA_PATH = Path(__file__).parent / "data" / "mc_maze.nwb"


@pytest.fixture
def engine():
    """Create a playback engine instance for testing."""
    if not DATA_PATH.exists():
        pytest.skip(f"Test data not found at {DATA_PATH}")
    return PlaybackEngine(DATA_PATH)


class TestPlaybackEngine:
    """Test PlaybackEngine class."""
    
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.data_path == DATA_PATH
        assert engine.loader is None
        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine._current_index == 0
        assert engine._sequence_number == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, engine):
        """Test starting and stopping the engine."""
        await engine.start()
        assert engine.is_running is True
        assert engine.loader is not None
        
        engine.stop()
        assert engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_pause_resume(self, engine):
        """Test pausing and resuming playback."""
        await engine.start()
        
        engine.pause()
        assert engine.is_paused is True
        
        engine.resume()
        assert engine.is_paused is False
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_reset(self, engine):
        """Test resetting playback to start."""
        await engine.start()
        
        # Advance a bit
        async for _ in engine.stream(loop=False):
            break
        
        assert engine._current_index > 0 or engine._sequence_number > 0
        
        engine.reset()
        assert engine._current_index == 0
        assert engine._sequence_number == 0
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_seek(self, engine):
        """Test seeking to specific time."""
        await engine.start()
        
        # Seek to 5 seconds
        engine.seek(5.0)
        assert engine._current_index > 0
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_stream_generates_packets(self, engine):
        """Test that stream generates valid packets."""
        await engine.start()
        
        packet_count = 0
        async for packet in engine.stream(loop=False):
            assert isinstance(packet, StreamPacket)
            assert packet.timestamp > 0
            assert packet.sequence_number >= 0
            assert len(packet.spikes.channel_ids) > 0
            assert len(packet.spikes.spike_counts) > 0
            
            packet_count += 1
            if packet_count >= 5:
                break
        
        assert packet_count == 5
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_sequence_numbers_increment(self, engine):
        """Test that sequence numbers increment monotonically."""
        await engine.start()
        
        prev_seq = -1
        packet_count = 0
        async for packet in engine.stream(loop=False):
            assert packet.sequence_number == prev_seq + 1
            prev_seq = packet.sequence_number
            
            packet_count += 1
            if packet_count >= 10:
                break
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_timing_accuracy(self, engine):
        """Test that packets are delivered at approximately 40Hz."""
        await engine.start()
        
        timestamps = []
        packet_count = 0
        async for packet in engine.stream(loop=False):
            timestamps.append(time.time())
            packet_count += 1
            if packet_count >= 10:
                break
        
        # Calculate intervals between packets
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals)
        
        # Should be approximately 25ms (40Hz)
        # Allow some tolerance for system variance
        expected_interval = 0.025  # 25ms
        assert abs(avg_interval - expected_interval) < 0.010  # Within 10ms tolerance
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_filter_by_target(self, engine):
        """Test filtering stream by target ID."""
        await engine.start()
        
        target_id = 0
        packet_count = 0
        async for packet in engine.stream(loop=False, target_filter=target_id):
            # All packets should have the specified target
            assert packet.intention.target_id == target_id
            
            packet_count += 1
            if packet_count >= 5:
                break
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_filter_by_trial(self, engine):
        """Test filtering stream by trial ID."""
        await engine.start()
        
        # Get first trial ID
        if engine.loader:
            trials = engine.loader.get_trials()
            if trials:
                trial_id = trials[0]['trial_id']
                
                packet_count = 0
                async for packet in engine.stream(loop=False, trial_filter=trial_id):
                    assert packet.trial_id == trial_id
                    
                    packet_count += 1
                    if packet_count >= 5:
                        break
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_pause_stops_streaming(self, engine):
        """Test that pausing stops packet delivery."""
        await engine.start()
        
        # Get a couple packets
        packet_count = 0
        async for packet in engine.stream(loop=False):
            packet_count += 1
            if packet_count >= 2:
                engine.pause()
                break
        
        # Resume and continue
        engine.resume()
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_get_metadata(self, engine):
        """Test getting stream metadata."""
        await engine.start()
        
        metadata = engine.get_metadata()
        
        assert metadata.num_channels > 0
        assert metadata.duration_seconds > 0
        assert metadata.frequency_hz > 0
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_starts_idempotent(self, engine):
        """Test that multiple start calls are safe."""
        await engine.start()
        await engine.start()  # Should be idempotent
        assert engine.is_running is True
        
        engine.stop()
    
    @pytest.mark.asyncio
    async def test_stop_before_start(self, engine):
        """Test stopping before starting."""
        engine.stop()  # Should not raise error
        assert engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_data_consistency(self, engine):
        """Test that data dimensions are consistent."""
        await engine.start()
        
        num_channels = None
        packet_count = 0
        async for packet in engine.stream(loop=False):
            if num_channels is None:
                num_channels = len(packet.spikes.channel_ids)
            
            # All packets should have same number of channels
            assert len(packet.spikes.channel_ids) == num_channels
            assert len(packet.spikes.spike_counts) == num_channels
            
            packet_count += 1
            if packet_count >= 10:
                break
        
        engine.stop()


class TestPerformance:
    """Test playback engine performance."""
    
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, engine):
        """Test sustained 40Hz throughput."""
        await engine.start()
        
        start_time = time.time()
        packet_count = 0
        target_packets = 80  # 2 seconds at 40Hz
        
        async for packet in engine.stream(loop=False):
            packet_count += 1
            if packet_count >= target_packets:
                break
        
        elapsed = time.time() - start_time
        
        # Should take approximately 2 seconds
        # Allow 10% tolerance for system variance
        assert 1.8 < elapsed < 2.2
        
        engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
