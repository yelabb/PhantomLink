# PhantomLink Binary Streaming - Quick Reference

## Endpoints

```
JSON:    ws://localhost:8000/stream/{session_code}
Binary:  ws://localhost:8000/stream/binary/{session_code}
```

## Python Client (3 lines)

```python
import websockets, msgpack, asyncio

async def stream():
    async with websockets.connect("ws://localhost:8000/stream/binary/my-session") as ws:
        packet = msgpack.unpackb(await ws.recv(), raw=False)
        
asyncio.run(stream())
```

## JavaScript Client (3 lines)

```javascript
import msgpack from 'msgpack-lite';
const ws = new WebSocket('ws://localhost:8000/stream/binary/my-session');
ws.onmessage = (e) => console.log(msgpack.decode(new Uint8Array(e.data)));
```

## Performance

| Metric | JSON | Binary | Gain |
|--------|------|--------|------|
| Size | 15KB | 6KB | **60%↓** |
| Speed | 1x | 3-5x | **3-5x** |
| CPU | High | Low | **Minimal** |

## Packet Structure

```python
{
    "sequence_number": 42,
    "trial_id": 12,
    "timestamp": 1673625600.123,
    
    "spikes": {
        "channel_ids": [0, 1, 2, ...],     # 142 channels
        "spike_counts": [3, 0, 5, ...],    # int32 counts
        "bin_size_ms": 25
    },
    
    "kinematics": {
        "x": 10.5, "y": 5.2,               # Position (cm)
        "vx": 0.15, "vy": -0.08            # Velocity (cm/ms)
    },
    
    "intention": {
        "target_id": 3,                    # Target index
        "target_x": 15.0, "target_y": 10.0, # Target pos
        "distance_to_target": 5.8          # Distance (cm)
    },
    
    "trial_time_ms": 1500                  # Time in trial
}
```

## Filters

```python
# Filter by target
ws://localhost:8000/stream/binary/my-session?target_id=0

# Filter by trial
ws://localhost:8000/stream/binary/my-session?trial_id=5
```

## Installation

```bash
pip install websockets msgpack          # Python
npm install ws msgpack-lite             # Node.js
```

## Examples

```bash
# Test endpoints
python scripts/test_endpoints.py

# Binary client demo
python examples/binary_client_example.py

# Compare with JSON
python examples/msgpack_client_example.py  # Binary
python examples/lsl_client_example.py      # JSON
```

## Docs

- 📖 Full Guide: [BINARY_STREAMING_GUIDE.md](BINARY_STREAMING_GUIDE.md)
- 📊 Implementation: [BINARY_IMPLEMENTATION_SUMMARY.md](BINARY_IMPLEMENTATION_SUMMARY.md)
- 🚀 README: [../README.md](../README.md)

## Common Patterns

### Buffered Processing

```python
buffer = []
async for msg in websocket:
    packet = msgpack.unpackb(msg, raw=False)
    buffer.append(packet)
    
    if len(buffer) >= 40:  # 1 second at 40Hz
        process_batch(buffer)
        buffer.clear()
```

### Reconnection

```python
while True:
    try:
        async with websockets.connect(uri) as ws:
            async for msg in ws:
                process(msgpack.unpackb(msg, raw=False))
    except websockets.exceptions.ConnectionClosed:
        await asyncio.sleep(5)  # Retry in 5s
```

### Error Handling

```python
try:
    packet = msgpack.unpackb(msg, raw=False)
except msgpack.exceptions.ExtraData:
    logger.warning("Malformed packet")
except Exception as e:
    logger.error(f"Error: {e}")
```

---

**Pro Tip**: Use binary endpoint for production, JSON for debugging! 🚀
