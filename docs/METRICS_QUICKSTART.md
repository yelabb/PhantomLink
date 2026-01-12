# Quick Start: Testing /metrics Endpoint

## Prerequisites
- PhantomLink server running on `http://localhost:8000`
- At least one active session with streaming data

## Step-by-Step Testing

### 1. Start the Server

```powershell
# From project root
python main.py
```

Expected output:
```
INFO: Starting PhantomLink Core server
INFO: Server ready on 0.0.0.0:8000
```

### 2. Create a Test Session

```powershell
# Create a new session
curl -X POST http://localhost:8000/api/sessions/create
```

Expected response:
```json
{
  "session_code": "swift-neural-42",
  "stream_url": "ws://localhost:8000/stream/swift-neural-42",
  "created": 1705075200.123
}
```

### 3. Start Streaming (Optional - for realistic metrics)

**Option A: Using Python WebSocket Client**

```python
# examples/test_metrics_streaming.py
import asyncio
import websockets
import msgpack

async def stream_test():
    uri = "ws://localhost:8000/stream/swift-neural-42"
    async with websockets.connect(uri) as websocket:
        # Receive first 100 packets
        for i in range(100):
            data = await websocket.recv()
            packet = msgpack.unpackb(data, raw=False)
            if i % 10 == 0:
                print(f"Received packet {i}: {packet['type']}")
        
        print("Streaming test complete!")

asyncio.run(stream_test())
```

**Option B: Using the LSL Client Example**

```powershell
python examples/lsl_client_example.py
```

### 4. Query the /metrics Endpoint

**Simple Query:**
```powershell
curl http://localhost:8000/metrics
```

**Pretty Print (with jq):**
```powershell
curl http://localhost:8000/metrics | jq
```

**Extract Specific Metrics:**
```powershell
# Get latency for all sessions
curl -s http://localhost:8000/metrics | jq '.metrics.sessions[].network_latency_ms'

# Get memory usage
curl -s http://localhost:8000/metrics | jq '.metrics.sessions[].memory_usage_mb'

# Get dropped packets
curl -s http://localhost:8000/metrics | jq '.metrics.sessions[].dropped_packets'
```

### 5. Use the Metrics Monitor Script

```powershell
python examples/metrics_monitor.py
```

Expected output:
```
🎯 Starting PhantomLink metrics monitor...
📊 Fetching metrics every 10 seconds
Press Ctrl+C to stop

================================================================================
📊 PhantomLink Metrics - 2026-01-12 14:30:00
================================================================================

🌐 Global Stats:
  Total Sessions: 1
  Active Sessions: 1
  Total Connections: 1

📡 Session: swift-neural-42
  ──────────────────────────────────────────────────────────────────────
  Status: 🟢 Running
  Connections: 1

  📦 Packets:
    Sent: 400
    Dropped: 0 (0.000%)

  ⚡ Network Latency:
    Mean: 1.234ms
    Std:  0.456ms
    Max:  3.789ms
```

## Expected Metrics Values (Healthy System)

### Network Latency
- **Mean**: 1-3 ms (excellent)
- **Std**: 0.2-0.5 ms (stable)
- **Max**: < 10 ms (acceptable)

### Timing Error
- **Mean**: 0.1-0.5 ms (precise)
- **Std**: 0.1-0.3 ms (consistent)
- **Max**: < 2 ms (good)

### Memory Usage
- **Per Session**: 5-20 MB (normal)
- **Total (10 sessions)**: < 200 MB (healthy)

### Dropped Packets
- **Count**: 0 (ideal)
- **Rate**: < 0.1% (acceptable)

## Troubleshooting

### Issue: No metrics data

**Symptom:**
```json
{
  "metrics": {
    "total_sessions": 0,
    "sessions": {}
  }
}
```

**Solution:**
1. Create a session: `curl -X POST http://localhost:8000/api/sessions/create`
2. Start streaming to generate metrics

### Issue: High latency (> 10ms)

**Possible causes:**
- System overload (check CPU/memory)
- Network congestion
- Too many concurrent sessions

**Solution:**
```powershell
# Check system resources
curl http://localhost:8000/api/stats

# Cleanup idle sessions
curl -X POST http://localhost:8000/api/sessions/cleanup

# Reduce sessions or increase hardware resources
```

### Issue: High memory usage (> 50MB per session)

**Possible causes:**
- Long-running sessions with large metric buffers
- Memory leak (rare)

**Solution:**
```powershell
# Restart the session
curl -X DELETE http://localhost:8000/api/sessions/swift-neural-42
curl -X POST http://localhost:8000/api/sessions/create
```

### Issue: 503 Service Unavailable

**Symptom:**
```json
{
  "detail": "Session manager not initialized"
}
```

**Solution:**
- Server not fully started - wait 2-3 seconds after launch
- Check server logs for initialization errors

## Automated Testing Script

```powershell
# test_metrics_endpoint.ps1

Write-Host "Testing /metrics endpoint..." -ForegroundColor Cyan

# 1. Check server health
Write-Host "`n1. Checking server health..." -ForegroundColor Yellow
$health = curl -s http://localhost:8000/health | ConvertFrom-Json
Write-Host "   Status: $($health.status)" -ForegroundColor Green

# 2. Create test session
Write-Host "`n2. Creating test session..." -ForegroundColor Yellow
$session = curl -s -X POST http://localhost:8000/api/sessions/create | ConvertFrom-Json
Write-Host "   Session: $($session.session_code)" -ForegroundColor Green

# 3. Query metrics (immediately - should have minimal data)
Write-Host "`n3. Querying metrics..." -ForegroundColor Yellow
$metrics = curl -s http://localhost:8000/metrics | ConvertFrom-Json
$sessionMetrics = $metrics.metrics.sessions.PSObject.Properties.Value | Select-Object -First 1

Write-Host "   Total Sessions: $($metrics.metrics.total_sessions)" -ForegroundColor Green
Write-Host "   Packets Sent: $($sessionMetrics.packets_sent)" -ForegroundColor Green
Write-Host "   Memory Usage: $($sessionMetrics.memory_usage_mb) MB" -ForegroundColor Green

# 4. Start brief streaming (requires Python websocket client)
Write-Host "`n4. Starting brief streaming..." -ForegroundColor Yellow
Write-Host "   (Manual step: run a WebSocket client for 10 seconds)" -ForegroundColor Gray

# 5. Query metrics again
Write-Host "`n5. Querying metrics after streaming..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$metrics2 = curl -s http://localhost:8000/metrics | ConvertFrom-Json
$sessionMetrics2 = $metrics2.metrics.sessions.PSObject.Properties.Value | Select-Object -First 1

if ($sessionMetrics2.packets_sent -gt 0) {
    Write-Host "   ✅ Packets Sent: $($sessionMetrics2.packets_sent)" -ForegroundColor Green
    Write-Host "   ✅ Latency: $([math]::Round($sessionMetrics2.network_latency_ms.mean, 2)) ms" -ForegroundColor Green
    Write-Host "   ✅ Memory: $([math]::Round($sessionMetrics2.memory_usage_mb, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No packets sent yet" -ForegroundColor Yellow
}

Write-Host "`n✅ Metrics endpoint test complete!" -ForegroundColor Cyan
```

## Integration with Monitoring Tools

### Prometheus
See [METRICS_GUIDE.md](../docs/METRICS_GUIDE.md#integration-with-monitoring-systems) for Prometheus integration.

### Grafana
Create dashboards using the JSON API endpoint.

### Custom Monitoring
Use the Python example in [examples/metrics_monitor.py](../examples/metrics_monitor.py).

## Next Steps

1. ✅ Test basic metrics retrieval
2. ✅ Generate realistic load (streaming for 1+ minute)
3. ✅ Monitor metrics during load test
4. ✅ Set up alerts for threshold violations
5. ✅ Integrate with monitoring system (optional)

## Support

For issues or questions:
- Check [METRICS_GUIDE.md](../docs/METRICS_GUIDE.md)
- Review [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md)
- Open an issue on GitHub
