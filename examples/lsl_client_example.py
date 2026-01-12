"""
Example LSL client for receiving PhantomLink neural data streams.

This demonstrates how to connect to PhantomLink's LSL streams using pylsl.
"""
import time
import numpy as np
from pylsl import StreamInlet, resolve_stream


def main():
    """Connect to PhantomLink LSL streams and receive data."""
    
    # Configuration - adjust session_code to match your session
    session_code = "swift-neural-42"  # Change this to your session code
    
    print("=" * 60)
    print("PhantomLink LSL Client Example")
    print("=" * 60)
    print(f"\nSearching for LSL streams from session '{session_code}'...")
    
    # Resolve neural stream
    print("\n1. Resolving Neural stream...")
    neural_streams = resolve_stream('type', 'EEG')
    
    if not neural_streams:
        print("❌ No neural streams found!")
        print("   Make sure PhantomLink server is running and a WebSocket client is connected.")
        return
    
    # Filter for our session
    target_stream = None
    for stream in neural_streams:
        if session_code in stream.name():
            target_stream = stream
            break
    
    if not target_stream:
        print(f"❌ No stream found for session '{session_code}'")
        print(f"   Available streams: {[s.name() for s in neural_streams]}")
        return
    
    print(f"✓ Found stream: {target_stream.name()}")
    print(f"  - Type: {target_stream.type()}")
    print(f"  - Channels: {target_stream.channel_count()}")
    print(f"  - Sample Rate: {target_stream.nominal_srate()} Hz")
    
    # Create inlet
    neural_inlet = StreamInlet(target_stream)
    
    # Optional: Resolve and connect to kinematics and intention streams
    print("\n2. Resolving Kinematics stream...")
    kin_streams = resolve_stream('type', 'Kinematics')
    kinematics_inlet = None
    
    for stream in kin_streams:
        if session_code in stream.name():
            print(f"✓ Found stream: {stream.name()}")
            kinematics_inlet = StreamInlet(stream)
            break
    
    print("\n3. Resolving Intention stream...")
    int_streams = resolve_stream('type', 'Markers')
    intention_inlet = None
    
    for stream in int_streams:
        if session_code in stream.name():
            print(f"✓ Found stream: {stream.name()}")
            intention_inlet = StreamInlet(stream)
            break
    
    # Stream data
    print("\n" + "=" * 60)
    print("Streaming neural data at 40Hz (press Ctrl+C to stop)")
    print("=" * 60)
    
    packet_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Pull neural sample
            neural_sample, neural_timestamp = neural_inlet.pull_sample(timeout=1.0)
            
            if neural_sample is None:
                print("⚠ No data received (timeout). Is the stream still active?")
                continue
            
            packet_count += 1
            
            # Optionally pull kinematics and intention
            kin_sample = None
            int_sample = None
            
            if kinematics_inlet:
                kin_sample, _ = kinematics_inlet.pull_sample(timeout=0.0)
            
            if intention_inlet:
                int_sample, _ = intention_inlet.pull_sample(timeout=0.0)
            
            # Display every 40 packets (1 second of data)
            if packet_count % 40 == 0:
                elapsed = time.time() - start_time
                rate = packet_count / elapsed
                
                print(f"\n📊 Packet #{packet_count} (Rate: {rate:.1f} Hz)")
                print(f"   LSL Timestamp: {neural_timestamp:.3f}")
                
                # Neural data
                spike_counts = np.array(neural_sample, dtype=np.int32)
                total_spikes = np.sum(spike_counts)
                active_channels = np.count_nonzero(spike_counts)
                print(f"   Neural: {total_spikes} total spikes across {active_channels}/{len(spike_counts)} active channels")
                print(f"           First 5 channels: {spike_counts[:5]}")
                
                # Kinematics
                if kin_sample:
                    print(f"   Kinematics: vx={kin_sample[0]:.2f}, vy={kin_sample[1]:.2f}, "
                          f"x={kin_sample[2]:.2f}, y={kin_sample[3]:.2f}")
                
                # Intention
                if int_sample:
                    target_id = int(int_sample[0])
                    trial_id = int(int_sample[3])
                    if target_id >= 0:
                        print(f"   Intention: Target {target_id} at ({int_sample[1]:.1f}, {int_sample[2]:.1f}), Trial {trial_id}")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
        elapsed = time.time() - start_time
        print(f"\nStats:")
        print(f"  - Total packets: {packet_count}")
        print(f"  - Duration: {elapsed:.1f}s")
        print(f"  - Average rate: {packet_count/elapsed:.1f} Hz")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. PhantomLink server is running (python main.py)")
        print("  2. A WebSocket client is connected to start LSL streaming")
        print("  3. pylsl is installed (pip install pylsl)")
