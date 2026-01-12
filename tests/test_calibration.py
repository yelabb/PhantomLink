"""
Test client for intent-based calibration workflows.

Demonstrates how to query trials and filter streams by target intention.
"""
import asyncio
import requests
import json


def test_trial_endpoints():
    """Test REST API endpoints for trial/intention queries."""
    base_url = "http://localhost:8000"
    
    print("=== Testing Trial/Intention API ===\n")
    
    # Get all trials
    print("1. Fetching all trials...")
    response = requests.get(f"{base_url}/api/trials")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {data['count']} trials")
        print(f"   Sample trial: {json.dumps(data['trials'][0], indent=2)}\n")
    else:
        print(f"   ERROR: {response.status_code}\n")
        return
    
    # Get specific trial
    trial_id = 5
    print(f"2. Fetching trial {trial_id}...")
    response = requests.get(f"{base_url}/api/trials/{trial_id}")
    if response.status_code == 200:
        trial = response.json()
        print(f"   Trial {trial_id} details:")
        print(f"   - Time: {trial['start_time']:.2f}s to {trial['stop_time']:.2f}s")
        print(f"   - Targets: {trial['num_targets']}")
        print(f"   - Active target: {trial['active_target']}")
        print(f"   - Target position: {trial['target_pos']}")
        print(f"   - Success: {trial['success']}\n")
    else:
        print(f"   ERROR: {response.status_code}\n")
    
    # Get trials by target
    target_index = 0
    print(f"3. Fetching all trials reaching for target {target_index}...")
    response = requests.get(f"{base_url}/api/trials/by-target/{target_index}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {data['count']} trials reaching for target {target_index}")
        if data['count'] > 0:
            print(f"   First trial: ID={data['trials'][0]['trial_id']}, "
                  f"time={data['trials'][0]['start_time']:.2f}s\n")
    else:
        print(f"   ERROR: {response.status_code}\n")
    
    print("=== Trial API Test Complete ===\n")


async def test_filtered_stream(target_id: int = 0, duration: int = 5):
    """
    Test streaming packets filtered by target intention.
    
    Args:
        target_id: Only stream packets when reaching for this target
        duration: Test duration in seconds
    """
    import websockets
    import time
    
    uri = f"ws://localhost:8000/stream?target_id={target_id}"
    print(f"=== Testing Filtered Stream (target_id={target_id}) ===\n")
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Receiving filtered stream...\n")
            
            packets_received = 0
            start_time = time.time()
            target_positions = []
            
            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data['type'] == 'metadata':
                        print("Stream metadata received")
                        continue
                    
                    if data['type'] == 'data':
                        packet = data['data']
                        packets_received += 1
                        
                        # Verify filter is working
                        if packet['intention']['target_id'] == target_id:
                            target_pos = (packet['intention']['target_x'], 
                                        packet['intention']['target_y'])
                            if target_pos not in target_positions:
                                target_positions.append(target_pos)
                        
                        # Print progress
                        if packets_received % 20 == 0:
                            print(f"  {packets_received} packets | "
                                  f"trial_id={packet['trial_id']} | "
                                  f"target=({packet['intention']['target_x']:.0f}, "
                                  f"{packet['intention']['target_y']:.0f})", end='\r')
                
                except asyncio.TimeoutError:
                    break
            
            print(f"\n\n=== Results ===")
            print(f"Packets received: {packets_received}")
            print(f"Unique target positions: {len(target_positions)}")
            for i, pos in enumerate(target_positions):
                print(f"  Target {i}: ({pos[0]:.0f}, {pos[1]:.0f})")
            print()
    
    except Exception as e:
        print(f"Error: {e}\n")


async def test_trial_filtered_stream(trial_id: int = 0):
    """
    Test streaming packets from a specific trial.
    
    Args:
        trial_id: Only stream packets from this trial
    """
    import websockets
    import time
    
    uri = f"ws://localhost:8000/stream?trial_id={trial_id}"
    print(f"=== Testing Trial-Filtered Stream (trial_id={trial_id}) ===\n")
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Receiving trial-filtered stream...\n")
            
            packets_received = 0
            first_time = None
            last_time = None
            
            while packets_received < 200:  # Limit to prevent infinite loop
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    
                    if data['type'] == 'metadata':
                        continue
                    
                    if data['type'] == 'data':
                        packet = data['data']
                        
                        # Verify correct trial
                        if packet['trial_id'] != trial_id:
                            print(f"ERROR: Received packet from trial {packet['trial_id']}, "
                                  f"expected {trial_id}")
                            break
                        
                        packets_received += 1
                        trial_time = packet['trial_time_ms']
                        
                        if first_time is None:
                            first_time = trial_time
                        last_time = trial_time
                        
                        if packets_received % 10 == 0:
                            print(f"  {packets_received} packets | "
                                  f"trial_time={trial_time:.0f}ms", end='\r')
                
                except asyncio.TimeoutError:
                    print(f"\n\nTimeout - likely end of trial")
                    break
            
            print(f"\n\n=== Results ===")
            print(f"Packets received: {packets_received}")
            if first_time and last_time:
                print(f"Trial duration: {(last_time - first_time)/1000:.2f}s")
                print(f"Time range: {first_time:.0f}ms to {last_time:.0f}ms")
            print()
    
    except Exception as e:
        print(f"Error: {e}\n")


if __name__ == "__main__":
    import sys
    
    # Test REST API first
    print("\n" + "="*60)
    print("PhantomLink Calibration API Test")
    print("="*60 + "\n")
    
    test_trial_endpoints()
    
    # Test filtered streaming
    print("\n" + "="*60)
    print("Testing Intent-Based Streaming")
    print("="*60 + "\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "target":
            target = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            asyncio.run(test_filtered_stream(target_id=target, duration=10))
        elif sys.argv[1] == "trial":
            trial = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            asyncio.run(test_trial_filtered_stream(trial_id=trial))
    else:
        # Default: test target-filtered stream
        asyncio.run(test_filtered_stream(target_id=0, duration=5))
