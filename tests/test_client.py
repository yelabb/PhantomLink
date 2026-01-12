"""
Test client for PhantomLink Core WebSocket streaming.

This client connects to the server and validates the 40Hz stream integrity.
"""
import asyncio
import json
import time
import statistics
from typing import List
import websockets


class StreamValidator:
    """Validates the integrity of the 40Hz data stream."""
    
    def __init__(self):
        self.packets_received = 0
        self.timestamps: List[float] = []
        self.sequence_numbers: List[int] = []
        self.intervals: List[float] = []
        self.start_time = None
        
    def process_packet(self, packet_data: dict):
        """Process and validate a single packet."""
        current_time = time.time()
        
        if self.start_time is None:
            self.start_time = current_time
        
        self.packets_received += 1
        self.timestamps.append(current_time)
        self.sequence_numbers.append(packet_data['sequence_number'])
        
        # Calculate interval from last packet
        if len(self.timestamps) > 1:
            interval = self.timestamps[-1] - self.timestamps[-2]
            self.intervals.append(interval * 1000)  # Convert to ms
        
        # Validate packet structure
        assert 'spikes' in packet_data, "Missing spikes data"
        assert 'kinematics' in packet_data, "Missing kinematics data"
        assert 'intention' in packet_data, "Missing intention data"
        
        # Validate spike data
        spikes = packet_data['spikes']
        assert 'channel_ids' in spikes, "Missing channel_ids"
        assert 'spike_counts' in spikes, "Missing spike_counts"
        assert len(spikes['channel_ids']) == len(spikes['spike_counts']), \
            "Channel count mismatch"
        
        # Validate kinematics
        kinematics = packet_data['kinematics']
        assert 'vx' in kinematics and 'vy' in kinematics, "Missing velocity data"
        
        # Validate intention
        intention = packet_data['intention']
        assert 'target_id' in intention, "Missing target_id"
    
    def get_stats(self) -> dict:
        """Get validation statistics."""
        if not self.intervals:
            return {}
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        actual_rate = self.packets_received / elapsed if elapsed > 0 else 0
        
        return {
            'packets_received': self.packets_received,
            'elapsed_seconds': elapsed,
            'actual_rate_hz': actual_rate,
            'target_rate_hz': 40,
            'rate_error_percent': abs(actual_rate - 40) / 40 * 100,
            'interval_mean_ms': statistics.mean(self.intervals),
            'interval_std_ms': statistics.stdev(self.intervals) if len(self.intervals) > 1 else 0,
            'interval_min_ms': min(self.intervals),
            'interval_max_ms': max(self.intervals),
            'target_interval_ms': 25.0,
            'sequence_gaps': self._check_sequence_gaps()
        }
    
    def _check_sequence_gaps(self) -> int:
        """Check for gaps in sequence numbers."""
        if len(self.sequence_numbers) < 2:
            return 0
        
        gaps = 0
        for i in range(1, len(self.sequence_numbers)):
            expected = self.sequence_numbers[i-1] + 1
            if self.sequence_numbers[i] != expected:
                gaps += 1
        
        return gaps


async def test_stream(uri: str = "ws://localhost:8000/stream", duration: int = 10):
    """
    Test the WebSocket stream for a specified duration.
    
    Args:
        uri: WebSocket URI
        duration: Test duration in seconds
    """
    validator = StreamValidator()
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Receiving stream...")
            
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data['type'] == 'metadata':
                        print("\n=== Stream Metadata ===")
                        metadata = data['data']
                        for key, value in metadata.items():
                            print(f"  {key}: {value}")
                        print()
                    
                    elif data['type'] == 'data':
                        validator.process_packet(data['data'])
                        
                        # Print progress every second
                        if validator.packets_received % 40 == 0:
                            elapsed = time.time() - start_time
                            rate = validator.packets_received / elapsed
                            print(f"  {validator.packets_received} packets | "
                                  f"{elapsed:.1f}s | "
                                  f"{rate:.1f} Hz", end='\r')
                
                except asyncio.TimeoutError:
                    print("\nTimeout waiting for packet")
                    break
                except json.JSONDecodeError as e:
                    print(f"\nError decoding JSON: {e}")
                    continue
            
            print("\n\n=== Validation Results ===")
            stats = validator.get_stats()
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")
            
            # Validate timing
            print("\n=== Timing Analysis ===")
            interval_error = abs(stats['interval_mean_ms'] - 25.0)
            rate_error = abs(stats['actual_rate_hz'] - 40.0)
            
            if interval_error < 2.0:  # Within 2ms tolerance
                print(f"  ✓ Interval timing: PASS ({stats['interval_mean_ms']:.2f}ms ≈ 25ms)")
            else:
                print(f"  ✗ Interval timing: FAIL ({stats['interval_mean_ms']:.2f}ms vs 25ms)")
            
            if rate_error < 1.0:  # Within 1Hz tolerance
                print(f"  ✓ Stream rate: PASS ({stats['actual_rate_hz']:.2f}Hz ≈ 40Hz)")
            else:
                print(f"  ✗ Stream rate: FAIL ({stats['actual_rate_hz']:.2f}Hz vs 40Hz)")
            
            if stats['sequence_gaps'] == 0:
                print(f"  ✓ Sequence integrity: PASS (no gaps)")
            else:
                print(f"  ✗ Sequence integrity: FAIL ({stats['sequence_gaps']} gaps)")
            
            print("\n=== Test Complete ===")
    
    except Exception as e:
        print(f"\nError: {e}")


async def sample_packets(uri: str = "ws://localhost:8000/stream", num_packets: int = 5):
    """
    Receive a few sample packets and print their structure.
    
    Args:
        uri: WebSocket URI
        num_packets: Number of packets to sample
    """
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Sampling packets...\n")
            
            received = 0
            
            while received < num_packets + 1:  # +1 for metadata
                message = await websocket.recv()
                data = json.loads(message)
                
                if data['type'] == 'metadata':
                    print("=== Metadata ===")
                    print(json.dumps(data['data'], indent=2))
                    print()
                
                elif data['type'] == 'data':
                    print(f"=== Packet {received + 1} ===")
                    packet = data['data']
                    
                    # Print compact summary
                    print(f"Timestamp: {packet['timestamp']}")
                    print(f"Sequence: {packet['sequence_number']}")
                    print(f"Spikes: {len(packet['spikes']['spike_counts'])} channels")
                    print(f"  Sample counts: {packet['spikes']['spike_counts'][:5]}...")
                    print(f"Kinematics: vx={packet['kinematics']['vx']:.2f}, "
                          f"vy={packet['kinematics']['vy']:.2f}")
                    print(f"Intention: target_id={packet['intention']['target_id']}, "
                          f"target_pos=({packet['intention']['target_x']:.1f}, "
                          f"{packet['intention']['target_y']:.1f})")
                    print()
                    
                    received += 1
            
            print("=== Sample Complete ===")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        # Sample mode: print a few packets
        asyncio.run(sample_packets(num_packets=3))
    else:
        # Test mode: validate stream for duration
        duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        asyncio.run(test_stream(duration=duration))
