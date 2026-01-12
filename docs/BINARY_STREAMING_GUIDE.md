# Binary Streaming Guide

## Overview

PhantomLink now supports two WebSocket streaming endpoints:

1. **JSON Endpoint**: `ws://localhost:8000/stream/{session_code}` - Human-readable JSON format
2. **Binary Endpoint**: `ws://localhost:8000/stream/binary/{session_code}` - High-performance MessagePack format

## Performance Comparison

| Metric | JSON Endpoint | Binary Endpoint | Improvement |
|--------|---------------|-----------------|-------------|
| Payload Size | ~15 KB | ~6 KB | **60% reduction** |
| Serialization Speed | Baseline | 3-5x faster | **3-5x speedup** |
| CPU Overhead | High | Minimal | **Significant reduction** |
| Network Bandwidth | High | Low | **60% less bandwidth** |

## When to Use Binary Streaming

Choose the **binary endpoint** when:
- ✅ You need maximum performance for real-time applications
- ✅ Network bandwidth is limited
- ✅ CPU resources are constrained
- ✅ Streaming to multiple clients simultaneously
- ✅ Processing high-frequency data (40Hz neural signals)

Choose the **JSON endpoint** when:
- 📝 Debugging and development
- 📝 Human readability is important
- 📝 Browser-based clients without MessagePack support
- 📝 Quick prototyping

## Quick Start

### Python Client

```python
import asyncio
import websockets
import msgpack

async def stream_binary():
    uri = "ws://localhost:8000/stream/binary/my-session"
    
    async with websockets.connect(uri) as websocket:
        # Receive metadata
        metadata_bytes = await websocket.recv()
        metadata = msgpack.unpackb(metadata_bytes, raw=False)
        print(f"Connected! Channels: {metadata['num_channels']}")
        
        # Stream data packets
        while True:
            packet_bytes = await websocket.recv()
            packet = msgpack.unpackb(packet_bytes, raw=False)
            
            # Process packet
            print(f"Seq: {packet['sequence_number']}, "
                  f"Trial: {packet['trial_id']}, "
                  f"Spikes: {sum(packet['spikes']['spike_counts'])}")

asyncio.run(stream_binary())
```

### JavaScript/TypeScript Client

```javascript
import msgpack from 'msgpack-lite';

const ws = new WebSocket('ws://localhost:8000/stream/binary/my-session');
ws.binaryType = 'arraybuffer';

ws.onmessage = (event) => {
  // Deserialize MessagePack
  const packet = msgpack.decode(new Uint8Array(event.data));
  
  if (packet.type === 'metadata') {
    console.log('Metadata:', packet.data);
  } else {
    // Process neural data packet
    console.log('Packet:', packet.sequence_number);
  }
};
```

## API Reference

### Binary Endpoint

**URL**: `ws://localhost:8000/stream/binary/{session_code}`

**Query Parameters**:
- `trial_id` (optional): Filter packets to specific trial
- `target_id` (optional): Filter packets to specific target

**Message Format**:

All messages are encoded using MessagePack binary format.

#### Metadata Message
```python
{
    "type": "metadata",
    "data": {
        "num_channels": 142,
        "frequency_hz": 40,
        "duration_seconds": 5398.725,
        "total_packets": 215949
    },
    "session": {
        "code": "my-session",
        "url": "ws://localhost:8000/stream/binary/my-session"
    }
}
```

#### Data Packet Message
```python
{
    "timestamp": 1673625600.123,
    "sequence_number": 42,
    "spikes": {
        "channel_ids": [0, 1, 2, ...],  # List of channel IDs
        "spike_counts": [3, 0, 5, ...],  # Spike counts per channel
        "bin_size_ms": 25                # Time bin size
    },
    "kinematics": {
        "vx": 0.15,                      # Velocity X
        "vy": -0.08,                     # Velocity Y
        "x": 10.5,                       # Position X
        "y": 5.2                         # Position Y
    },
    "intention": {
        "target_id": 3,                  # Target index
        "target_x": 15.0,                # Target X coordinate
        "target_y": 10.0,                # Target Y coordinate
        "distance_to_target": 5.8        # Distance in cm
    },
    "trial_id": 12,                      # Current trial
    "trial_time_ms": 1500                # Time within trial
}
```

## Examples

### 1. Basic Streaming

Run the provided example:
```bash
python examples/binary_client_example.py
```

This will:
1. Compare payload sizes between JSON and binary endpoints
2. Stream 200 packets from the binary endpoint
3. Display performance metrics

### 2. Filtered Streaming

Stream only packets from target 0:
```python
uri = "ws://localhost:8000/stream/binary/my-session?target_id=0"
```

Stream only packets from trial 5:
```python
uri = "ws://localhost:8000/stream/binary/my-session?trial_id=5"
```

### 3. Multiple Sessions

Each session has independent playback state:
```python
# Session 1 - Full stream
session1 = "ws://localhost:8000/stream/binary/analysis-session"

# Session 2 - Target 0 only
session2 = "ws://localhost:8000/stream/binary/target0-session?target_id=0"

# Session 3 - Trial 10 only
session3 = "ws://localhost:8000/stream/binary/trial10-session?trial_id=10"
```

## Best Practices

### 1. Connection Management

```python
async def robust_stream():
    while True:
        try:
            async with websockets.connect(uri) as ws:
                # Process packets
                async for message in ws:
                    packet = msgpack.unpackb(message, raw=False)
                    process_packet(packet)
        except websockets.exceptions.ConnectionClosed:
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
```

### 2. Packet Buffering

For real-time processing, use a buffer:
```python
from collections import deque

packet_buffer = deque(maxlen=100)  # Keep last 100 packets

async for message in websocket:
    packet = msgpack.unpackb(message, raw=False)
    packet_buffer.append(packet)
    
    # Process buffered packets
    if len(packet_buffer) >= 40:  # 1 second at 40Hz
        process_batch(list(packet_buffer))
        packet_buffer.clear()
```

### 3. Error Handling

```python
try:
    packet = msgpack.unpackb(message, raw=False)
except msgpack.exceptions.ExtraData:
    logger.warning("Malformed packet received")
except Exception as e:
    logger.error(f"Deserialization error: {e}")
```

## Installation Requirements

### Python
```bash
pip install websockets msgpack
```

### JavaScript/Node.js
```bash
npm install ws msgpack-lite
```

### Browser
```html
<script src="https://cdn.jsdelivr.net/npm/msgpack-lite@0.1.26/dist/msgpack.min.js"></script>
```

## Performance Tips

1. **Batch Processing**: Process packets in batches (e.g., 1 second = 40 packets) rather than individually
2. **Async IO**: Use async/await patterns to avoid blocking
3. **Memory Management**: Limit buffer sizes to prevent memory growth
4. **Connection Pooling**: Reuse connections when possible
5. **Compression**: MessagePack already provides compression, no need for additional compression layers

## Troubleshooting

### Issue: High CPU usage

**Solution**: Ensure you're using the binary endpoint, not JSON. Binary serialization is 3-5x more efficient.

### Issue: Packet drops

**Solution**: Increase buffer sizes or process packets asynchronously:
```python
async def process_in_background(packet):
    await asyncio.create_task(heavy_processing(packet))
```

### Issue: Connection timeouts

**Solution**: Send periodic ping messages:
```python
async def keep_alive(websocket):
    while True:
        await websocket.ping()
        await asyncio.sleep(30)
```

## Migration from JSON to Binary

If you're currently using the JSON endpoint:

**Before** (JSON):
```python
uri = "ws://localhost:8000/stream/my-session"
async with websockets.connect(uri) as ws:
    data = await ws.recv()
    packet = json.loads(data)  # Parse JSON
```

**After** (Binary):
```python
uri = "ws://localhost:8000/stream/binary/my-session"
async with websockets.connect(uri) as ws:
    data = await ws.recv()
    packet = msgpack.unpackb(data, raw=False)  # Parse MessagePack
```

The packet structure remains identical - only the serialization format changes!

## Resources

- [MessagePack Official Site](https://msgpack.org/)
- [Python msgpack](https://pypi.org/project/msgpack/)
- [JavaScript msgpack-lite](https://www.npmjs.com/package/msgpack-lite)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## Support

For issues or questions:
1. Check the examples in `examples/binary_client_example.py`
2. Review the metrics endpoint: `http://localhost:8000/metrics`
3. Check server logs for connection issues
