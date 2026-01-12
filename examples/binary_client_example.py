"""
Binary WebSocket client example for PhantomLink Core.

This example demonstrates how to connect to the binary streaming endpoint
and deserialize MessagePack-encoded neural data packets.

Performance benefits:
- 60% smaller payload size compared to JSON
- 3-5x faster serialization/deserialization
- Lower CPU overhead for high-frequency streaming
"""
import asyncio
import websockets
import msgpack
import time
from datetime import datetime


async def consume_binary_stream(session_code="swift-neural-42", max_packets=100):
    """
    Connect to the binary WebSocket endpoint and consume neural data packets.
    
    Args:
        session_code: Session identifier for isolated playback
        max_packets: Maximum number of packets to receive (None for infinite)
    """
    uri = f"ws://localhost:8000/stream/binary/{session_code}"
    
    print(f"Connecting to binary stream: {uri}")
    print("-" * 80)
    
    packet_count = 0
    start_time = time.time()
    
    async with websockets.connect(uri) as websocket:
        print("✓ Connected to binary stream")
        
        # Receive initial metadata
        metadata_bytes = await websocket.recv()
        metadata = msgpack.unpackb(metadata_bytes, raw=False)
        
        print("\n📊 Session Metadata:")
        print(f"  Channels: {metadata.get('num_channels', 'N/A')}")
        print(f"  Frequency: {metadata.get('frequency_hz', 'N/A')} Hz")
        print(f"  Duration: {metadata.get('duration_seconds', 'N/A')} seconds")
        print(f"  Total packets: {metadata.get('total_packets', 'N/A')}")
        print("\n" + "=" * 80)
        print("Streaming neural data packets (MessagePack binary format)...")
        print("=" * 80 + "\n")
        
        # Stream data packets
        while max_packets is None or packet_count < max_packets:
            try:
                # Receive binary packet
                packet_bytes = await websocket.recv()
                
                # Deserialize MessagePack
                packet = msgpack.unpackb(packet_bytes, raw=False)
                
                packet_count += 1
                
                # Display packet info every 10 packets
                if packet_count % 10 == 0:
                    spikes = packet['spikes']
                    kinematics = packet['kinematics']
                    intention = packet['intention']
                    
                    elapsed = time.time() - start_time
                    rate = packet_count / elapsed if elapsed > 0 else 0
                    
                    print(f"Packet #{packet_count:4d} | "
                          f"Seq: {packet['sequence_number']:6d} | "
                          f"Trial: {packet['trial_id']:2d} | "
                          f"Target: {intention['target_id']:2d} | "
                          f"Vel: ({kinematics['vx']:+.2f}, {kinematics['vy']:+.2f}) | "
                          f"Rate: {rate:.1f} pkt/s")
                    
                    # Display spike activity summary
                    spike_counts = spikes['spike_counts']
                    total_spikes = sum(spike_counts)
                    active_channels = sum(1 for count in spike_counts if count > 0)
                    
                    if packet_count % 40 == 0:  # Every second at 40Hz
                        print(f"  └─ Spikes: {total_spikes} total, {active_channels}/{len(spike_counts)} channels active")
                
            except websockets.exceptions.ConnectionClosed:
                print("\n⚠️  Connection closed by server")
                break
            except KeyboardInterrupt:
                print("\n⏸  Stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Error processing packet: {e}")
                break
        
        # Summary
        elapsed = time.time() - start_time
        avg_rate = packet_count / elapsed if elapsed > 0 else 0
        
        print("\n" + "=" * 80)
        print("📈 Streaming Summary:")
        print(f"  Total packets received: {packet_count}")
        print(f"  Duration: {elapsed:.2f} seconds")
        print(f"  Average rate: {avg_rate:.1f} packets/second")
        print(f"  Expected rate: 40 packets/second (40Hz)")
        print("=" * 80)


async def compare_payload_sizes(session_code="swift-neural-42", num_packets=10):
    """
    Compare payload sizes between JSON and binary endpoints.
    
    This demonstrates the ~60% size reduction with MessagePack.
    """
    print("\n🔬 Payload Size Comparison Test")
    print("=" * 80)
    
    # Test binary endpoint
    binary_uri = f"ws://localhost:8000/stream/binary/{session_code}"
    binary_sizes = []
    
    print(f"\n1️⃣  Testing Binary Endpoint: {binary_uri}")
    async with websockets.connect(binary_uri) as ws:
        # Skip metadata
        await ws.recv()
        
        for i in range(num_packets):
            data = await ws.recv()
            binary_sizes.append(len(data))
    
    # Test JSON endpoint
    json_uri = f"ws://localhost:8000/stream/{session_code}"
    json_sizes = []
    
    print(f"2️⃣  Testing JSON Endpoint: {json_uri}")
    async with websockets.connect(json_uri) as ws:
        # Skip metadata
        await ws.recv()
        
        for i in range(num_packets):
            data = await ws.recv()
            json_sizes.append(len(data))
    
    # Results
    avg_binary = sum(binary_sizes) / len(binary_sizes)
    avg_json = sum(json_sizes) / len(json_sizes)
    reduction = ((avg_json - avg_binary) / avg_json) * 100
    
    print("\n" + "=" * 80)
    print("📊 Results:")
    print(f"  Binary (MessagePack): {avg_binary:.0f} bytes/packet")
    print(f"  JSON:                 {avg_json:.0f} bytes/packet")
    print(f"  Size reduction:       {reduction:.1f}%")
    print(f"  Compression factor:   {avg_json/avg_binary:.2f}x")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    # Run streaming test
    print("\n🚀 PhantomLink Binary Streaming Client")
    print("=" * 80)
    
    # Create session code with timestamp for isolation
    session_code = f"binary-test-{datetime.now().strftime('%H%M%S')}"
    
    try:
        # First, compare payload sizes
        asyncio.run(compare_payload_sizes(session_code, num_packets=10))
        
        print("\n" + "=" * 80)
        input("Press Enter to start streaming test (Ctrl+C to stop)...")
        
        # Then stream packets
        asyncio.run(consume_binary_stream(session_code, max_packets=200))
        
    except KeyboardInterrupt:
        print("\n\n✅ Test completed")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
