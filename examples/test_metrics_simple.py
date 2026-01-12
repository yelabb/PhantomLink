"""
Simple test to verify /metrics endpoint is working

Run this after starting the server to verify the metrics implementation.
"""

import requests
import time


def test_metrics_endpoint():
    """Test the /metrics endpoint"""
    
    print("🧪 Testing PhantomLink /metrics endpoint...\n")
    
    base_url = "http://localhost:8000"
    
    # 1. Check server health
    print("1️⃣ Checking server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is healthy\n")
        else:
            print(f"   ❌ Server returned status {response.status_code}\n")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Cannot connect to server: {e}\n")
        print("   💡 Make sure the server is running: python main.py\n")
        return False
    
    # 2. Create a test session
    print("2️⃣ Creating test session...")
    try:
        response = requests.post(f"{base_url}/api/sessions/create", timeout=5)
        if response.status_code == 200:
            session_data = response.json()
            session_code = session_data['session_code']
            print(f"   ✅ Session created: {session_code}\n")
        else:
            print(f"   ❌ Failed to create session: {response.status_code}\n")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error creating session: {e}\n")
        return False
    
    # 3. Query metrics endpoint (initial)
    print("3️⃣ Querying /metrics endpoint...")
    try:
        response = requests.get(f"{base_url}/metrics", timeout=5)
        if response.status_code == 200:
            metrics = response.json()
            print("   ✅ Metrics endpoint accessible\n")
            
            # Check structure
            print("4️⃣ Validating response structure...")
            required_keys = ['timestamp', 'service', 'version', 'metrics']
            for key in required_keys:
                if key in metrics:
                    print(f"   ✅ '{key}' present")
                else:
                    print(f"   ❌ '{key}' missing")
                    return False
            
            print("\n5️⃣ Checking metrics data...")
            metrics_data = metrics['metrics']
            
            # Check global metrics
            print(f"   Total Sessions: {metrics_data['total_sessions']}")
            print(f"   Active Sessions: {metrics_data['active_sessions']}")
            print(f"   Total Connections: {metrics_data['total_connections']}")
            
            # Check session-specific metrics
            if metrics_data['sessions']:
                print(f"\n6️⃣ Session metrics for '{session_code}':")
                session_metrics = metrics_data['sessions'].get(session_code)
                
                if session_metrics:
                    print(f"   ✅ Session found in metrics")
                    print(f"   Packets Sent: {session_metrics['packets_sent']}")
                    print(f"   Dropped Packets: {session_metrics['dropped_packets']}")
                    print(f"   Memory Usage: {session_metrics['memory_usage_mb']:.2f} MB")
                    print(f"   Is Running: {session_metrics['is_running']}")
                    print(f"   Connections: {session_metrics['connections']}")
                    
                    # Check latency metrics (may be empty if no streaming yet)
                    if 'network_latency_ms' in session_metrics:
                        latency = session_metrics['network_latency_ms']
                        print(f"\n   Network Latency:")
                        print(f"     Mean: {latency['mean']:.3f} ms")
                        print(f"     Std:  {latency['std']:.3f} ms")
                        print(f"     Max:  {latency['max']:.3f} ms")
                    
                    if 'timing_error_ms' in session_metrics:
                        timing = session_metrics['timing_error_ms']
                        print(f"\n   Timing Error:")
                        print(f"     Mean: {timing['mean']:.3f} ms")
                        print(f"     Std:  {timing['std']:.3f} ms")
                        print(f"     Max:  {timing['max']:.3f} ms")
                else:
                    print(f"   ⚠️  Session not found in metrics (this is OK for new sessions)")
            else:
                print("   ⚠️  No session metrics yet (start streaming to generate metrics)")
            
            print("\n" + "="*60)
            print("✅ All tests passed!")
            print("="*60)
            
            # Print next steps
            print("\n📚 Next Steps:")
            print("1. Start streaming to generate realistic metrics:")
            print(f"   python examples/lsl_client_example.py")
            print("\n2. Monitor metrics in real-time:")
            print(f"   python examples/metrics_monitor.py")
            print("\n3. View detailed metrics guide:")
            print(f"   docs/METRICS_GUIDE.md")
            
            return True
            
        else:
            print(f"   ❌ Metrics endpoint returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error querying metrics: {e}\n")
        return False


if __name__ == "__main__":
    success = test_metrics_endpoint()
    exit(0 if success else 1)
