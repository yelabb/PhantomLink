"""
Unit tests for data models (models.py).

Tests Pydantic model validation, serialization, and field constraints.
"""
import pytest
from pydantic import ValidationError
from phantomlink.models import SpikeData, Kinematics, TargetIntention, StreamPacket


class TestSpikeData:
    """Test SpikeData model."""
    
    def test_valid_spike_data(self):
        """Test creation of valid spike data."""
        spike_data = SpikeData(
            channel_ids=[1, 2, 3, 4],
            spike_counts=[5, 3, 8, 2],
            bin_size_ms=25.0
        )
        assert len(spike_data.channel_ids) == 4
        assert len(spike_data.spike_counts) == 4
        assert spike_data.bin_size_ms == 25.0
    
    def test_default_bin_size(self):
        """Test default bin size value."""
        spike_data = SpikeData(
            channel_ids=[1, 2],
            spike_counts=[3, 4]
        )
        assert spike_data.bin_size_ms == 25.0
    
    def test_empty_arrays(self):
        """Test spike data with empty arrays."""
        spike_data = SpikeData(
            channel_ids=[],
            spike_counts=[]
        )
        assert len(spike_data.channel_ids) == 0
        assert len(spike_data.spike_counts) == 0
    
    def test_serialization(self):
        """Test JSON serialization."""
        spike_data = SpikeData(
            channel_ids=[1, 2],
            spike_counts=[5, 3]
        )
        json_data = spike_data.model_dump()
        assert json_data['channel_ids'] == [1, 2]
        assert json_data['spike_counts'] == [5, 3]
        assert json_data['bin_size_ms'] == 25.0


class TestKinematics:
    """Test Kinematics model."""
    
    def test_velocity_only(self):
        """Test kinematics with only velocity (minimum required)."""
        kin = Kinematics(vx=0.5, vy=-0.3)
        assert kin.vx == 0.5
        assert kin.vy == -0.3
        assert kin.x is None
        assert kin.y is None
    
    def test_full_kinematics(self):
        """Test kinematics with position and velocity."""
        kin = Kinematics(vx=0.5, vy=-0.3, x=10.0, y=20.0)
        assert kin.vx == 0.5
        assert kin.vy == -0.3
        assert kin.x == 10.0
        assert kin.y == 20.0
    
    def test_zero_velocity(self):
        """Test zero velocity values."""
        kin = Kinematics(vx=0.0, vy=0.0)
        assert kin.vx == 0.0
        assert kin.vy == 0.0
    
    def test_negative_values(self):
        """Test negative velocities and positions."""
        kin = Kinematics(vx=-1.5, vy=-2.3, x=-5.0, y=-10.0)
        assert kin.vx == -1.5
        assert kin.vy == -2.3
        assert kin.x == -5.0
        assert kin.y == -10.0


class TestTargetIntention:
    """Test TargetIntention model."""
    
    def test_all_none(self):
        """Test target intention with all optional fields as None."""
        intention = TargetIntention()
        assert intention.target_id is None
        assert intention.target_x is None
        assert intention.target_y is None
        assert intention.distance_to_target is None
    
    def test_full_intention(self):
        """Test target intention with all fields populated."""
        intention = TargetIntention(
            target_id=3,
            target_x=100.0,
            target_y=200.0,
            distance_to_target=50.5
        )
        assert intention.target_id == 3
        assert intention.target_x == 100.0
        assert intention.target_y == 200.0
        assert intention.distance_to_target == 50.5
    
    def test_partial_intention(self):
        """Test target intention with some fields."""
        intention = TargetIntention(
            target_id=1,
            distance_to_target=25.0
        )
        assert intention.target_id == 1
        assert intention.target_x is None
        assert intention.target_y is None
        assert intention.distance_to_target == 25.0


class TestStreamPacket:
    """Test StreamPacket model."""
    
    def test_minimal_packet(self):
        """Test minimal valid stream packet."""
        packet = StreamPacket(
            timestamp=1234567890.5,
            sequence_number=42,
            spikes=SpikeData(channel_ids=[1, 2], spike_counts=[3, 4]),
            kinematics=Kinematics(vx=0.1, vy=0.2),
            intention=TargetIntention()
        )
        assert packet.timestamp == 1234567890.5
        assert packet.sequence_number == 42
        assert packet.trial_id is None
        assert packet.trial_time_ms is None
    
    def test_full_packet(self):
        """Test stream packet with all fields."""
        packet = StreamPacket(
            timestamp=1234567890.5,
            sequence_number=42,
            spikes=SpikeData(
                channel_ids=[1, 2, 3],
                spike_counts=[5, 3, 8],
                bin_size_ms=25.0
            ),
            kinematics=Kinematics(vx=0.5, vy=-0.3, x=100.0, y=200.0),
            intention=TargetIntention(
                target_id=2,
                target_x=150.0,
                target_y=250.0,
                distance_to_target=70.7
            ),
            trial_id=10,
            trial_time_ms=1500.0
        )
        assert packet.timestamp == 1234567890.5
        assert packet.sequence_number == 42
        assert len(packet.spikes.channel_ids) == 3
        assert packet.kinematics.x == 100.0
        assert packet.intention.target_id == 2
        assert packet.trial_id == 10
        assert packet.trial_time_ms == 1500.0
    
    def test_serialization_roundtrip(self):
        """Test serialization and deserialization."""
        original = StreamPacket(
            timestamp=1234567890.5,
            sequence_number=42,
            spikes=SpikeData(channel_ids=[1, 2], spike_counts=[3, 4]),
            kinematics=Kinematics(vx=0.1, vy=0.2),
            intention=TargetIntention(target_id=1)
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back
        restored = StreamPacket(**data)
        
        assert restored.timestamp == original.timestamp
        assert restored.sequence_number == original.sequence_number
        assert restored.spikes.channel_ids == original.spikes.channel_ids
        assert restored.kinematics.vx == original.kinematics.vx
        assert restored.intention.target_id == original.intention.target_id
    
    def test_missing_required_fields(self):
        """Test that required fields raise validation errors."""
        with pytest.raises(ValidationError):
            StreamPacket(
                # Missing timestamp
                sequence_number=42,
                spikes=SpikeData(channel_ids=[1], spike_counts=[2]),
                kinematics=Kinematics(vx=0.1, vy=0.2),
                intention=TargetIntention()
            )
        
        with pytest.raises(ValidationError):
            StreamPacket(
                timestamp=1234567890.5,
                # Missing sequence_number
                spikes=SpikeData(channel_ids=[1], spike_counts=[2]),
                kinematics=Kinematics(vx=0.1, vy=0.2),
                intention=TargetIntention()
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
