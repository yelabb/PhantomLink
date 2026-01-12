"""
Example: Real-time metrics monitoring for PhantomLink

This script demonstrates how to monitor system performance metrics
including latency, memory usage, and dropped packets.

Usage:
    python metrics_monitor.py
"""

import time
import requests
from typing import Dict, Any
from datetime import datetime


class MetricsMonitor:
    """Monitor PhantomLink metrics in real-time."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics_url = f"{base_url}/metrics"
        
        # Alert thresholds
        self.thresholds = {
            'latency_ms': 10.0,           # Alert if latency > 10ms
            'dropped_rate': 0.01,         # Alert if > 1% packet loss
            'memory_mb': 50.0,            # Alert if memory > 50MB
            'timing_error_ms': 5.0        # Alert if timing error > 5ms
        }
    
    def fetch_metrics(self) -> Dict[str, Any]:
        """Fetch current metrics from server."""
        try:
            response = requests.get(self.metrics_url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching metrics: {e}")
            return None
    
    def check_alerts(self, session_code: str, session_metrics: Dict) -> list:
        """Check if any metrics exceed alert thresholds."""
        alerts = []
        
        # Check network latency
        latency = session_metrics['network_latency_ms']['mean']
        if latency > self.thresholds['latency_ms']:
            alerts.append(
                f"⚠️  High latency: {latency:.2f}ms (threshold: {self.thresholds['latency_ms']}ms)"
            )
        
        # Check memory usage
        memory = session_metrics['memory_usage_mb']
        if memory > self.thresholds['memory_mb']:
            alerts.append(
                f"⚠️  High memory usage: {memory:.2f}MB (threshold: {self.thresholds['memory_mb']}MB)"
            )
        
        # Check dropped packets
        packets_sent = session_metrics['packets_sent']
        dropped = session_metrics['dropped_packets']
        if packets_sent > 0:
            drop_rate = dropped / packets_sent
            if drop_rate > self.thresholds['dropped_rate']:
                alerts.append(
                    f"⚠️  High packet loss: {drop_rate*100:.2f}% ({dropped}/{packets_sent})"
                )
        
        # Check timing error
        timing_error = session_metrics['timing_error_ms']['mean']
        if timing_error > self.thresholds['timing_error_ms']:
            alerts.append(
                f"⚠️  High timing error: {timing_error:.2f}ms (threshold: {self.thresholds['timing_error_ms']}ms)"
            )
        
        return alerts
    
    def display_metrics(self, metrics: Dict[str, Any]):
        """Display metrics in a formatted way."""
        timestamp = datetime.fromtimestamp(metrics['timestamp'])
        print(f"\n{'='*80}")
        print(f"📊 PhantomLink Metrics - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        metrics_data = metrics['metrics']
        print(f"\n🌐 Global Stats:")
        print(f"  Total Sessions: {metrics_data['total_sessions']}")
        print(f"  Active Sessions: {metrics_data['active_sessions']}")
        print(f"  Total Connections: {metrics_data['total_connections']}")
        
        sessions = metrics_data['sessions']
        if not sessions:
            print("\n  No active sessions")
            return
        
        for session_code, session_metrics in sessions.items():
            print(f"\n📡 Session: {session_code}")
            print(f"  {'─'*70}")
            
            # Connection status
            status = "🟢 Running" if session_metrics['is_running'] else "🔴 Stopped"
            if session_metrics['is_paused']:
                status = "🟡 Paused"
            print(f"  Status: {status}")
            print(f"  Connections: {session_metrics['connections']}")
            
            # Packet statistics
            packets_sent = session_metrics['packets_sent']
            dropped = session_metrics['dropped_packets']
            drop_rate = (dropped / packets_sent * 100) if packets_sent > 0 else 0
            print(f"\n  📦 Packets:")
            print(f"    Sent: {packets_sent:,}")
            print(f"    Dropped: {dropped} ({drop_rate:.3f}%)")
            
            # Network latency
            latency = session_metrics['network_latency_ms']
            print(f"\n  ⚡ Network Latency:")
            print(f"    Mean: {latency['mean']:.3f}ms")
            print(f"    Std:  {latency['std']:.3f}ms")
            print(f"    Max:  {latency['max']:.3f}ms")
            
            # Timing error
            timing = session_metrics['timing_error_ms']
            print(f"\n  ⏱️  Timing Error:")
            print(f"    Mean: {timing['mean']:.3f}ms")
            print(f"    Std:  {timing['std']:.3f}ms")
            print(f"    Max:  {timing['max']:.3f}ms")
            
            # Memory usage
            memory = session_metrics['memory_usage_mb']
            print(f"\n  💾 Memory Usage: {memory:.2f} MB")
            
            # Check for alerts
            alerts = self.check_alerts(session_code, session_metrics)
            if alerts:
                print(f"\n  🚨 ALERTS:")
                for alert in alerts:
                    print(f"    {alert}")
    
    def monitor_continuously(self, interval_seconds: int = 10):
        """Monitor metrics continuously at specified interval."""
        print("🎯 Starting PhantomLink metrics monitor...")
        print(f"📊 Fetching metrics every {interval_seconds} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                metrics = self.fetch_metrics()
                if metrics:
                    self.display_metrics(metrics)
                else:
                    print(f"\n❌ Failed to fetch metrics at {datetime.now()}")
                
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped by user")


def main():
    """Main function."""
    # Create monitor
    monitor = MetricsMonitor(base_url="http://localhost:8000")
    
    # Start continuous monitoring (10 second intervals)
    monitor.monitor_continuously(interval_seconds=10)


if __name__ == "__main__":
    main()
