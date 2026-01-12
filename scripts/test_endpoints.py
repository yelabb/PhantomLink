"""
Test script to verify both JSON and binary streaming endpoints.

This script tests:
1. Connection to both endpoints
2. Metadata reception
3. Data packet reception
4. Deserialization correctness
"""
import asyncio
import websockets
import json
import msgpack
import sys


async def test_json_endpoint(session_code="test-json"):
    """Test JSON streaming endpoint."""
    uri = f"ws://localhost:8000/stream/{session_code}"
    print(f"\n🧪 Testing JSON endpoint: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Receive metadata
            metadata_raw = await websocket.recv()
            metadata = json.loads(metadata_raw)
            
            assert metadata.get("type") == "metadata", "First message should be metadata"
            assert "data" in metadata, "Metadata should have 'data' field"
            
            print(f"  ✓ Metadata received (JSON)")
            print(f"    - Channels: {metadata['data'].get('num_channels')}")
            print(f"    - Frequency: {metadata['data'].get('frequency_hz')} Hz")
            
            # Receive first data packet
            packet_raw = await websocket.recv()
            packet = json.loads(packet_raw)
            
            assert packet.get("type") == "data", "Second message should be data"
            assert "data" in packet, "Packet should have 'data' field"
            
            packet_data = packet["data"]
            assert "spikes" in packet_data, "Packet should have 'spikes'"
            assert "kinematics" in packet_data, "Packet should have 'kinematics'"
            assert "intention" in packet_data, "Packet should have 'intention'"
            
            print(f"  ✓ Data packet received (JSON)")
            print(f"    - Sequence: {packet_data.get('sequence_number')}")
            print(f"    - Trial: {packet_data.get('trial_id')}")
            print(f"    - Total spikes: {sum(packet_data['spikes']['spike_counts'])}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ JSON endpoint test failed: {e}")
        return False


async def test_binary_endpoint(session_code="test-binary"):
    """Test binary/MessagePack streaming endpoint."""
    uri = f"ws://localhost:8000/stream/binary/{session_code}"
    print(f"\n🧪 Testing Binary endpoint: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Receive metadata
            metadata_raw = await websocket.recv()
            metadata = msgpack.unpackb(metadata_raw, raw=False)
            
            assert "num_channels" in metadata or "data" in metadata, "Metadata should have channel info"
            
            print(f"  ✓ Metadata received (MessagePack)")
            # Handle both possible formats
            if "data" in metadata:
                print(f"    - Channels: {metadata['data'].get('num_channels')}")
                print(f"    - Frequency: {metadata['data'].get('frequency_hz')} Hz")
            else:
                print(f"    - Channels: {metadata.get('num_channels')}")
                print(f"    - Frequency: {metadata.get('frequency_hz')} Hz")
            
            # Receive first data packet
            packet_raw = await websocket.recv()
            packet = msgpack.unpackb(packet_raw, raw=False)
            
            assert "spikes" in packet, "Packet should have 'spikes'"
            assert "kinematics" in packet, "Packet should have 'kinematics'"
            assert "intention" in packet, "Packet should have 'intention'"
            
            print(f"  ✓ Data packet received (MessagePack)")
            print(f"    - Sequence: {packet.get('sequence_number')}")
            print(f"    - Trial: {packet.get('trial_id')}")
            print(f"    - Total spikes: {sum(packet['spikes']['spike_counts'])}")
            
            # Compare sizes
            json_size = len(json.dumps(packet).encode())
            msgpack_size = len(packet_raw)
            reduction = ((json_size - msgpack_size) / json_size) * 100
            
            print(f"  📊 Payload comparison:")
            print(f"    - JSON size: {json_size} bytes")
            print(f"    - MessagePack size: {msgpack_size} bytes")
            print(f"    - Reduction: {reduction:.1f}%")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Binary endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_filtered_stream(session_code="test-filtered"):
    """Test filtered streaming with query parameters."""
    uri = f"ws://localhost:8000/stream/binary/{session_code}?target_id=0"
    print(f"\n🧪 Testing Filtered stream: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Skip metadata
            await websocket.recv()
            
            # Check 5 packets
            target_ids = []
            for i in range(5):
                packet_raw = await websocket.recv()
                packet = msgpack.unpackb(packet_raw, raw=False)
                target_ids.append(packet['intention']['target_id'])
            
            # All should be target 0
            assert all(tid == 0 for tid in target_ids), f"Filter failed: got targets {set(target_ids)}"
            
            print(f"  ✓ Filter working correctly")
            print(f"    - All packets from target 0: {target_ids}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Filtered stream test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 80)
    print("PhantomLink WebSocket Endpoint Tests")
    print("=" * 80)
    print("\nMake sure the server is running: python main.py")
    print("=" * 80)
    
    results = []
    
    # Test JSON endpoint
    results.append(("JSON Endpoint", await test_json_endpoint()))
    
    # Test binary endpoint
    results.append(("Binary Endpoint", await test_binary_endpoint()))
    
    # Test filtered stream
    results.append(("Filtered Stream", await test_filtered_stream()))
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:20s} {status}")
    
    print("=" * 80)
    
    # Exit code
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
