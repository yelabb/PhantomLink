"""
Benchmark comparison: JSON vs MessagePack serialization performance.

This script demonstrates the performance gains of MessagePack over JSON
for neural data streaming at 40Hz with 142 channels.
"""
import json
import msgpack
import time
import numpy as np
from typing import List


def create_sample_packet(num_channels: int = 142) -> dict:
    """Create a realistic PhantomLink packet."""
    return {
        "timestamp": 30.875,
        "sequence_number": 1234,
        "spikes": {
            "channel_ids": list(range(num_channels)),
            "spike_counts": np.random.poisson(2, num_channels).tolist(),
            "bin_size_ms": 25.0
        },
        "kinematics": {
            "vx": 15.2,
            "vy": -8.4,
            "x": 125.3,
            "y": -78.9
        },
        "intention": {
            "target_id": 1,
            "target_x": -77.0,
            "target_y": 82.0,
            "distance_to_target": 45.3
        },
        "trial_id": 42,
        "trial_time_ms": 1250.0
    }


def benchmark_serialization(num_iterations: int = 1000):
    """Benchmark JSON vs MessagePack serialization."""
    print("=" * 70)
    print("PhantomLink Serialization Benchmark: JSON vs MessagePack")
    print("=" * 70)
    print(f"\nTest Configuration:")
    print(f"  Channels: 142")
    print(f"  Iterations: {num_iterations}")
    print(f"  Frequency: 40Hz (25ms/packet)")
    print()
    
    # Create test packet
    packet = create_sample_packet()
    
    # Benchmark JSON
    print("Benchmarking JSON...")
    json_sizes = []
    json_start = time.perf_counter()
    
    for _ in range(num_iterations):
        json_bytes = json.dumps(packet).encode('utf-8')
        json_sizes.append(len(json_bytes))
        _ = json.loads(json_bytes.decode('utf-8'))
    
    json_elapsed = time.perf_counter() - json_start
    json_avg_size = np.mean(json_sizes)
    
    # Benchmark MessagePack
    print("Benchmarking MessagePack...")
    msgpack_sizes = []
    msgpack_start = time.perf_counter()
    
    for _ in range(num_iterations):
        msgpack_bytes = msgpack.packb(packet, use_bin_type=True)
        msgpack_sizes.append(len(msgpack_bytes))
        _ = msgpack.unpackb(msgpack_bytes, raw=False)
    
    msgpack_elapsed = time.perf_counter() - msgpack_start
    msgpack_avg_size = np.mean(msgpack_sizes)
    
    # Calculate metrics
    size_reduction = (1 - msgpack_avg_size / json_avg_size) * 100
    speedup = json_elapsed / msgpack_elapsed
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n📦 Payload Size:")
    print(f"  JSON:        {json_avg_size:>8.0f} bytes")
    print(f"  MessagePack: {msgpack_avg_size:>8.0f} bytes")
    print(f"  Reduction:   {size_reduction:>8.1f}%")
    
    print(f"\n⚡ Serialization Speed:")
    print(f"  JSON:        {json_elapsed*1000:>8.2f} ms ({json_elapsed/num_iterations*1000:.3f} ms/packet)")
    print(f"  MessagePack: {msgpack_elapsed*1000:>8.2f} ms ({msgpack_elapsed/num_iterations*1000:.3f} ms/packet)")
    print(f"  Speedup:     {speedup:>8.2f}x faster")
    
    print(f"\n🌐 Bandwidth @ 40Hz:")
    json_bandwidth = json_avg_size * 40 / 1024  # KB/s
    msgpack_bandwidth = msgpack_avg_size * 40 / 1024  # KB/s
    print(f"  JSON:        {json_bandwidth:>8.1f} KB/s")
    print(f"  MessagePack: {msgpack_bandwidth:>8.1f} KB/s")
    print(f"  Saved:       {json_bandwidth - msgpack_bandwidth:>8.1f} KB/s per stream")
    
    print(f"\n💾 Storage (1 hour @ 40Hz):")
    json_storage = json_avg_size * 40 * 3600 / (1024**2)  # MB
    msgpack_storage = msgpack_avg_size * 40 * 3600 / (1024**2)  # MB
    print(f"  JSON:        {json_storage:>8.1f} MB")
    print(f"  MessagePack: {msgpack_storage:>8.1f} MB")
    print(f"  Saved:       {json_storage - msgpack_storage:>8.1f} MB")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print(f"\nMessagePack provides:")
    print(f"  ✓ {size_reduction:.0f}% smaller payload")
    print(f"  ✓ {speedup:.1f}x faster serialization")
    print(f"  ✓ {json_bandwidth - msgpack_bandwidth:.0f} KB/s bandwidth savings per stream")
    print(f"\nFor 10 concurrent streams:")
    print(f"  ✓ {(json_bandwidth - msgpack_bandwidth) * 10:.0f} KB/s total bandwidth savings")
    print(f"  ✓ {(json_storage - msgpack_storage) * 10:.0f} MB storage savings per hour")
    print()


if __name__ == "__main__":
    benchmark_serialization(num_iterations=1000)

