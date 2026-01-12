"""
Test client for multi-session functionality.

Demonstrates creating and using isolated sessions.
"""
import asyncio
import requests
import json
import websockets


def create_session(base_url: str = "http://localhost:8000", custom_code: str = None):
    """Create a new session and return the session code."""
    url = f"{base_url}/api/sessions/create"
    params = {"custom_code": custom_code} if custom_code else {}
    
    response = requests.post(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Created session: {data['session_code']}")
        print(f"  Stream URL: {data['stream_url']}")
        return data['session_code']
    else:
        print(f"✗ Error creating session: {response.status_code}")
        return None


def list_sessions(base_url: str = "http://localhost:8000"):
    """List all active sessions."""
    response = requests.get(f"{base_url}/api/sessions")
    if response.status_code == 200:
        data = response.json()
        print(f"\n=== Active Sessions ({data['stats']['total_sessions']}) ===")
        for session in data['sessions']:
            print(f"\nSession: {session['session_code']}")
            print(f"  Age: {session['age_seconds']:.0f}s")
            print(f"  Idle: {session['idle_seconds']:.0f}s")
            print(f"  Connections: {session['connections']}")
            print(f"  Running: {session['is_running']}")
            print(f"  Position: packet {session['current_index']} ({session['packets_sent']} sent)")
        
        print(f"\n=== Stats ===")
        stats = data['stats']
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print(f"✗ Error listing sessions: {response.status_code}")


async def test_session_stream(session_code: str, duration: int = 5):
    """Test streaming from a specific session."""
    uri = f"ws://localhost:8000/stream/{session_code}"
    print(f"\n=== Testing Session Stream: {session_code} ===")
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!\n")
            
            packets_received = 0
            start_time = None
            
            async for message in websocket:
                data = json.loads(message)
                
                if data['type'] == 'metadata':
                    print(f"Metadata received")
                    print(f"  Session: {data['session']['code']}")
                    print(f"  Channels: {data['data']['num_channels']}")
                    print(f"  Trials: {data['data']['num_trials']}")
                    start_time = asyncio.get_event_loop().time()
                    print()
                    continue
                
                if data['type'] == 'data':
                    packets_received += 1
                    
                    if packets_received % 20 == 0:
                        elapsed = asyncio.get_event_loop().time() - start_time
                        rate = packets_received / elapsed
                        print(f"  {packets_received} packets | {elapsed:.1f}s | {rate:.1f} Hz", end='\r')
                    
                    if start_time and (asyncio.get_event_loop().time() - start_time) >= duration:
                        break
            
            print(f"\n\n✓ Received {packets_received} packets in {duration}s")
    
    except Exception as e:
        print(f"✗ Error: {e}")


async def test_concurrent_sessions():
    """Test multiple sessions streaming concurrently."""
    print("\n=== Testing Concurrent Sessions ===\n")
    
    # Create 3 sessions
    sessions = []
    for i in range(3):
        code = create_session()
        if code:
            sessions.append(code)
        await asyncio.sleep(0.5)
    
    print(f"\nCreated {len(sessions)} sessions")
    
    # Stream from all simultaneously
    async def stream_session(code, duration=3):
        uri = f"ws://localhost:8000/stream/{code}"
        count = 0
        try:
            async with websockets.connect(uri) as ws:
                async for msg in ws:
                    data = json.loads(msg)
                    if data['type'] == 'data':
                        count += 1
                        if count >= duration * 40:  # 40Hz * duration
                            break
        except Exception as e:
            print(f"Error in {code}: {e}")
        print(f"  Session {code}: {count} packets")
    
    # Run all streams concurrently
    print("\nStreaming from all sessions simultaneously...")
    await asyncio.gather(*[stream_session(code, 5) for code in sessions])
    
    # Check session stats
    print("\nFinal session stats:")
    list_sessions()


async def test_session_isolation():
    """Test that sessions have independent state."""
    print("\n=== Testing Session Isolation ===\n")
    
    # Create two sessions
    session1 = create_session()
    session2 = create_session()
    
    # Stream from session1, pause it
    print(f"\nStreaming from {session1}...")
    uri1 = f"ws://localhost:8000/stream/{session1}"
    
    async with websockets.connect(uri1) as ws:
        count = 0
        async for msg in ws:
            data = json.loads(msg)
            if data['type'] == 'data':
                count += 1
                if count >= 50:  # Get 50 packets
                    break
    
    # Pause session1
    response = requests.post(f"http://localhost:8000/api/control/{session1}/pause")
    print(f"\n✓ Paused {session1}: {response.json()}")
    
    # Stream from session2 (should work independently)
    print(f"\nStreaming from {session2} (while {session1} is paused)...")
    uri2 = f"ws://localhost:8000/stream/{session2}"
    
    async with websockets.connect(uri2) as ws:
        count = 0
        async for msg in ws:
            data = json.loads(msg)
            if data['type'] == 'data':
                count += 1
                if count >= 50:
                    break
    
    print(f"✓ Received 50 packets from {session2}")
    print("\n✓ Sessions are isolated - session2 works while session1 is paused")
    
    # Cleanup
    requests.delete(f"http://localhost:8000/api/sessions/{session1}")
    requests.delete(f"http://localhost:8000/api/sessions/{session2}")
    print(f"\n✓ Cleaned up test sessions")


if __name__ == "__main__":
    import sys
    
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            custom_code = sys.argv[2] if len(sys.argv) > 2 else None
            create_session(base_url, custom_code)
        
        elif command == "list":
            list_sessions(base_url)
        
        elif command == "stream":
            session_code = sys.argv[2] if len(sys.argv) > 2 else None
            if not session_code:
                print("Usage: python test_multi_session.py stream <session_code>")
            else:
                asyncio.run(test_session_stream(session_code, duration=10))
        
        elif command == "concurrent":
            asyncio.run(test_concurrent_sessions())
        
        elif command == "isolation":
            asyncio.run(test_session_isolation())
        
        else:
            print("Unknown command")
            print("Usage: python test_multi_session.py [create|list|stream|concurrent|isolation]")
    
    else:
        # Default: run all tests
        print("\n" + "="*60)
        print("PhantomLink Multi-Session Test Suite")
        print("="*60)
        
        # Test 1: Create session
        print("\n[1/4] Creating session...")
        session_code = create_session(base_url)
        
        # Test 2: List sessions
        print("\n[2/4] Listing sessions...")
        list_sessions(base_url)
        
        # Test 3: Stream from session
        if session_code:
            print(f"\n[3/4] Testing stream from session...")
            asyncio.run(test_session_stream(session_code, duration=5))
        
        # Test 4: Session isolation
        print("\n[4/4] Testing session isolation...")
        asyncio.run(test_session_isolation())
        
        print("\n" + "="*60)
        print("✓ All tests complete")
        print("="*60)
