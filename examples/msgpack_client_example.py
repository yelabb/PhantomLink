"""
Example WebSocket client for PhantomLink with MessagePack support.

This demonstrates how to connect to PhantomLink's WebSocket stream
using the optimized MessagePack binary format (60% smaller payload, 3-5x faster).
"""
import asyncio
import websockets
import msgpack
import time
import numpy as np
from typing import Dict, Any


class PhantomLinkClient:
    """
    Async WebSocket client for PhantomLink with MessagePack deserialization.
    
    Features:
    - Binary MessagePack protocol (60% bandwidth reduction vs JSON)
    - Async streaming at 40Hz
    - Real-time neural data + ground truth
    """
    
    def __init__(self, session_code: str = "swift-neural-42", 
                 host: str = "localhost", port: int = 8000):
        """
        Initialize PhantomLink client.
        
        Args:
            session_code: Session identifier for isolated playback
            host: Server hostname
            port: Server port
        """
        self.session_code = session_code
        self.ws_url = f"ws://{host}:{port}/stream/{session_code}"
        self.websocket = None
        self.metadata = None
        self.packet_count = 0
        self.start_time = None
        
    async def connect(self):
        """Connect to PhantomLink WebSocket stream."""
        print(f"Connecting to {self.ws_url}...")
        self.websocket = await websockets.connect(self.ws_url)
        print("✓ Connected!")
        
        # Receive metadata (first message)
        binary_data = await self.websocket.recv()
        metadata_msg = msgpack.unpackb(binary_data, raw=False)
        
        if metadata_msg["type"] == "metadata":
            self.metadata = metadata_msg["data"]
            print("\n📋 Stream Metadata:")
            print(f"   Dataset: {self.metadata['dataset']}")
            print(f"   Channels: {self.metadata['num_channels']}")
            print(f"   Frequency: {self.metadata['frequency_hz']} Hz")
            print(f"   Duration: {self.metadata['duration_seconds']:.1f}s")
            print(f"   Total Packets: {self.metadata['total_packets']}")
            print(f"   Trials: {self.metadata['num_trials']}")
        
        self.start_time = time.time()
        
    async def stream(self, max_packets: int = None):
        """
        Stream data packets from PhantomLink.
        
        Args:
            max_packets: Maximum number of packets to receive (None = infinite)
        """
        if not self.websocket:
            raise RuntimeError("Not connected. Call connect() first.")
        
        print("\n" + "=" * 70)
        print("Streaming neural data at 40Hz (press Ctrl+C to stop)")
        print("=" * 70)
        
        try:
            while True:
                if max_packets and self.packet_count >= max_packets:
                    break
                
                # Receive binary MessagePack data
                binary_data = await self.websocket.recv()
                
                # Deserialize MessagePack (3-5x faster than JSON)
                message = msgpack.unpackb(binary_data, raw=False)
                
                if message["type"] == "data":
                    packet = message["data"]
                    self.packet_count += 1
                    
                    # Process packet
                    self._process_packet(packet)
                    
        except websockets.exceptions.ConnectionClosed:
            print("\n⚠ Connection closed by server")
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user")
        finally:
            await self.disconnect()
    
    def _process_packet(self, packet: Dict[str, Any]):
        """Process received data packet."""
        # Display stats every 40 packets (1 second)
        if self.packet_count % 40 == 0:
            elapsed = time.time() - self.start_time
            rate = self.packet_count / elapsed
            
            # Extract data
            spike_counts = np.array(packet["spikes"]["spike_counts"], dtype=np.int32)
            total_spikes = np.sum(spike_counts)
            active_channels = np.count_nonzero(spike_counts)
            
            kinematics = packet["kinematics"]
            intention = packet["intention"]
            
            print(f"\n📊 Packet #{packet['sequence_number']} (Rate: {rate:.1f} Hz)")
            print(f"   Timestamp: {packet['timestamp']:.3f}")
            print(f"   Neural: {total_spikes} spikes across {active_channels}/{len(spike_counts)} channels")
            print(f"           First 5 channels: {spike_counts[:5]}")
            print(f"   Kinematics: vx={kinematics['vx']:.2f}, vy={kinematics['vy']:.2f}, "
                  f"x={kinematics['x']:.2f}, y={kinematics['y']:.2f}")
            
            if intention["target_id"] is not None:
                print(f"   Intention: Target {intention['target_id']} at "
                      f"({intention['target_x']:.1f}, {intention['target_y']:.1f})")
            
            if packet["trial_id"] is not None:
                print(f"   Trial: {packet['trial_id']} @ {packet['trial_time_ms']:.0f}ms")
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            
            elapsed = time.time() - self.start_time
            print(f"\n📈 Session Statistics:")
            print(f"   Total packets: {self.packet_count}")
            print(f"   Duration: {elapsed:.1f}s")
            print(f"   Average rate: {self.packet_count/elapsed:.1f} Hz")
            print(f"   MessagePack savings: ~60% vs JSON")


async def main():
    """Main client loop."""
    # Configuration
    session_code = "swift-neural-42"  # Change to your session code
    
    print("=" * 70)
    print("PhantomLink WebSocket Client (MessagePack Binary Protocol)")
    print("=" * 70)
    print(f"Session: {session_code}")
    print("Protocol: MessagePack binary (60% smaller than JSON)")
    print()
    
    # Create and connect client
    client = PhantomLinkClient(session_code=session_code)
    
    try:
        await client.connect()
        await client.stream()  # Stream indefinitely
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PhantomLink server is running: python main.py")
        print("  2. Check session code is correct")
        print("  3. Verify msgpack is installed: pip install msgpack")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")

