# PhantomLink

Neural data streaming server for BCI development. Replays MC_Maze dataset at 40Hz via WebSocket and LSL protocols.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![Data Analysis](https://img.shields.io/badge/📊_Data_Analysis-Notebook-orange.svg)](notebooks/data_analysis.ipynb)
[![Beginner's Guide](https://img.shields.io/badge/📚_Beginner's_Guide-Learn-blue.svg)](docs/BEGINNERS_GUIDE.md)

**Status:** MVP Complete  
**Timing:** Soft real-time (1-15ms jitter)  
**Use Case:** Algorithm development, decoder training, testing

> **New to BCIs?** See [Beginner's Guide](docs/BEGINNERS_GUIDE.md) for educational introduction to BCIs and neural data.

[Quick Start](#quick-start) • [API Reference](#api-reference) • [Use Cases](#use-cases) • [Testing](#testing)

## Overview

Neural data streaming server for BCI development. Replays MC_Maze dataset (142 channels, 294s, 100 trials) at 40Hz.

**Core Functionality:**
- Stream neural spike counts, cursor kinematics, and target intentions
- Multi-session isolation with independent playback control
- Filter by target ID or trial ID for calibration
- REST API for session and playback control
- WebSocket and LSL streaming protocols

## Features

- **40Hz streaming** via WebSocket and LSL (1-15ms timing jitter)
- **MessagePack protocol** (60% smaller payloads vs JSON, 3-5x faster serialization)
- **Multi-session isolation** with auto-cleanup (1hr TTL)
- **Playback control** (pause/resume/seek per session)
- **Intent filtering** by target_id or trial_id
- **Trial metadata API** for calibration workflows
- **Noise injection** for robustness testing
- **Memory-mapped NWB/HDF5** lazy loading

### Data Format

Each 40Hz packet contains:
- **Spike Counts**: 142 neural channels (int32 array)
- **Kinematics**: Cursor position (x, y) and velocity (vx, vy)
- **Intention**: Target ID, position (target_x, target_y), and distance
- **Metadata**: Trial ID, timestamp, packet sequence number

**MessagePack Example (Python):**
```python
import msgpack
import websockets

async with websockets.connect("ws://localhost:8000/stream/swift-neural-42") as ws:
    binary_data = await ws.recv()
    packet = msgpack.unpackb(binary_data, raw=False)
    
    spike_counts = packet["data"]["spikes"]["spike_counts"]  # 142 channels
    kinematics = packet["data"]["kinematics"]  # {x, y, vx, vy}
    intention = packet["data"]["intention"]    # {target_id, target_x, target_y}
```

**Performance Gains (MessagePack vs JSON):**
- Payload size: ~15KB → ~6KB (60% reduction)
- Serialization: 3-5x faster
- Bandwidth: 600KB/s → 240KB/s at 40Hz

### Noise Injection

Test decoder robustness with realistic neural noise simulation:

**Configuration:**
```python
from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware

middleware = NoiseInjectionMiddleware(
    noise_std=0.5,              # Gaussian noise level
    drift_amplitude=0.3,         # Non-stationary drift (30%)
    drift_period_seconds=60.0,   # Drift cycle period
    enable_noise=True,
    enable_drift=True
)

engine = PlaybackEngine(data_path, noise_middleware=middleware)
```

**Stress Levels:**
- **Light**: `noise_std=0.2, drift_amplitude=0.1` - Minimal impairment
- **Moderate**: `noise_std=0.5, drift_amplitude=0.3` - Realistic conditions
- **Intense**: `noise_std=1.0, drift_amplitude=0.5` - Challenging scenarios
- **Extreme**: `noise_std=2.0, drift_amplitude=0.8` - Stress-test limits

**Applications:**
- Robustness testing under realistic noise
- Stress-testing algorithm boundaries
- Comparative analysis with/without noise
- Training data augmentation

See [examples/noise_injection_demo.py](examples/noise_injection_demo.py) and [NOISE_INJECTION_GUIDE.md](docs/NOISE_INJECTION_GUIDE.md) for details.

## Quick Start

### Prerequisites

- Python 3.12+
- ~2GB disk space for dataset

### Installation

```bash
git clone https://github.com/yelabb/PhantomLink.git
cd PhantomLink
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Download Dataset

```bash
pip install dandi
dandi download https://dandiarchive.org/dandiset/000140/draft
mkdir -p data/raw
mv 000140/sub-Jenkins/* data/raw/mc_maze.nwb
```

Expected: `data/raw/mc_maze.nwb` (~1.5GB)

### Start Server

```bash
python main.py
```

Server runs on `http://localhost:8000`. API docs at `/docs`.

### Test

```bash
python test_client.py 10  # Validate 40Hz streaming
```

## Architecture

```
FastAPI Server
├── SessionManager (multi-session, LRU eviction, 1hr TTL)
├── PlaybackEngine (40Hz asyncio, pause/resume/seek)
├── LSLStreamer (Lab Streaming Layer outlets)
└── DataLoader (lazy NWB/HDF5, memory-mapped)
    └── mc_maze.nwb (142 units, 294s)
```

**Components:**
- **server.py**: FastAPI app with REST + WebSocket endpoints
- **session_manager.py**: Multi-session orchestration, LRU eviction
- **playback_engine.py**: 40Hz asyncio streaming loop with intent filtering
- **lsl_streamer.py**: LSL outlet manager for neuroscience tools
- **data_loader.py**: Lazy NWB/HDF5 loader with trial metadata
- **models.py**: Pydantic data models for validation
- **config.py**: Configuration settings

**Stack:** FastAPI 0.109+, Uvicorn, PyNWB 2.6+, H5py, pylsl 1.16+, asyncio

**Performance:**
- Packet generation: ~7ms (HDF5 read + binning)
- Payload size: ~6KB (MessagePack)
- Timing variance: 1-15ms (OS-dependent)
- Memory: <500MB (memory-mapped, shared across sessions)
- Max sessions: 10 (configurable, LRU eviction)
- Session TTL: 3600s (1 hour auto-cleanup)

## API Reference

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "timestamp": "2026-01-12T13:30:00Z"
}
```

### Session Management

#### Create Session

```bash
# Auto-generated session code
curl -X POST http://localhost:8000/api/sessions/create

# Custom session code
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"custom_code": "my-experiment-1"}'
```

**Response:**
```json
{
  "session_code": "swift-neural-42",
  "stream_url": "ws://localhost:8000/stream/swift-neural-42",
  "created_at": "2026-01-12T13:30:00Z"
}
```

#### List Sessions

```bash
curl http://localhost:8000/api/sessions
```

**Response:**
```json
{
  "sessions": {
    "swift-neural-42": {
      "created_at": "2026-01-12T13:30:00Z",
      "last_accessed": "2026-01-12T13:32:15Z",
      "active_connections": 2,
      "is_running": true,
      "current_packet": 150
    }
  },
  "total_sessions": 1
}
```

#### Get Session Details

```bash
curl http://localhost:8000/api/sessions/{session_code}
```

#### Delete Session

```bash
curl -X DELETE http://localhost:8000/api/sessions/{session_code}
```

#### Cleanup Expired Sessions

```bash
curl -X POST http://localhost:8000/api/sessions/cleanup
```

### Metrics Endpoint

Monitor system performance with real-time metrics:

```bash
curl http://localhost:8000/metrics
```

**Response:**
```json
{
  "timestamp": 1705075200.123,
  "service": "PhantomLink Core",
  "version": "0.2.0",
  "metrics": {
    "total_sessions": 2,
    "active_sessions": 1,
    "total_connections": 1,
    "sessions": {
      "swift-neural-42": {
        "packets_sent": 15230,
        "dropped_packets": 3,
        "network_latency_ms": {
          "mean": 1.234,
          "std": 0.456,
          "max": 5.678
        },
        "timing_error_ms": {
          "mean": 0.123,
          "std": 0.089,
          "max": 2.345
        },
        "memory_usage_mb": 12.45,
        "is_running": true,
        "is_paused": false,
        "connections": 1
      }
    }
  }
}
```

**Key Metrics:**
- **network_latency_ms**: Tick-to-network latency (generation → send)
- **memory_usage_mb**: Memory consumed per session
- **dropped_packets**: Failed packet transmissions
- **timing_error_ms**: Deviation from target 40Hz timing

📊 See [METRICS_GUIDE.md](docs/METRICS_GUIDE.md) for detailed monitoring documentation.

### WebSocket Streaming

#### Connect to Stream

```javascript
const ws = new WebSocket('ws://localhost:8000/stream/swift-neural-42');

ws.onmessage = (event) => {
  const packet = JSON.parse(event.data);
  console.log('Packet:', packet.data.packet_id);
  console.log('Spikes:', packet.data.spikes.spike_counts);
  console.log('Position:', packet.data.kinematics.x, packet.data.kinematics.y);
  console.log('Target:', packet.data.intention.target_x, packet.data.intention.target_y);
};
```

#### Python MessagePack Client

```python
import msgpack
import websockets

async with websockets.connect("ws://localhost:8000/stream/swift-neural-42") as ws:
    binary_data = await ws.recv()
    packet = msgpack.unpackb(binary_data, raw=False)
    
    spike_counts = packet["data"]["spikes"]["spike_counts"]  # 142 channels
    kinematics = packet["data"]["kinematics"]  # {x, y, vx, vy}
    intention = packet["data"]["intention"]    # {target_id, target_x, target_y}
```

#### Filter by Target

```bash
ws://localhost:8000/stream/swift-neural-42?target_id=0
```

#### Filter by Trial

```bash
ws://localhost:8000/stream/swift-neural-42?trial_id=42
```

### LSL Streaming

PhantomLink creates LSL outlets for each session. Three streams per session:

- **PhantomLink-Neural-{session_code}**: Spike counts (142 channels, int32)
- **PhantomLink-Kinematics-{session_code}**: Cursor position and velocity (4 channels: vx, vy, x, y)
- **PhantomLink-Intention-{session_code}**: Target and trial markers (4 channels: target_id, target_x, target_y, trial_id)

#### Python LSL Client

```python
from pylsl import StreamInlet, resolve_stream

# Resolve neural stream
streams = resolve_stream('type', 'EEG')
inlet = StreamInlet(streams[0])

# Receive data at 40Hz
while True:
    sample, timestamp = inlet.pull_sample()
    print(f"Timestamp: {timestamp:.3f}, Spikes: {sample[:5]}...")
```

#### Configuration

```bash
# Disable LSL (WebSocket only)
set PHANTOM_LSL_ENABLED=false

# Customize stream names
set PHANTOM_LSL_STREAM_NAME=MyBCI-Stream
set PHANTOM_LSL_SOURCE_ID=MyBCI-001
```

### Playback Control

#### Pause Stream

```bash
curl -X POST http://localhost:8000/api/control/{session_code}/pause
```

#### Resume Stream

```bash
curl -X POST http://localhost:8000/api/control/{session_code}/resume
```

#### Seek to Position

```bash
curl -X POST http://localhost:8000/api/control/{session_code}/seek \
  -H "Content-Type: application/json" \
  -d '{"packet_id": 1000}'
```

#### Get Session Statistics

```bash
curl http://localhost:8000/api/stats/{session_code}
```

**Response:**
```json
{
  "session_code": "swift-neural-42",
  "is_running": true,
  "current_packet": 1234,
  "total_packets": 11748,
  "elapsed_seconds": 30.85,
  "active_connections": 2
}
```

### Trial Metadata

#### Get All Trials

```bash
curl http://localhost:8000/api/trials
```

**Response:**
```json
{
  "trials": [
    {
      "trial_id": 0,
      "start_time": 0.0,
      "stop_time": 2.95,
      "target_x": -118,
      "target_y": -83,
      "target_id": 0
    }
  ],
  "total_trials": 100
}
```

#### Get Trials by Target

```bash
curl http://localhost:8000/api/trials/by-target/{target_id}
```

#### Get Trial by ID

```bash
curl http://localhost:8000/api/trials/{trial_id}
```

## Use Cases

### 1. Decoder Training

Train BCI decoders with real neural data and known intentions:

```python
import websockets
import msgpack
import asyncio

async def train_decoder():
    async with websockets.connect("ws://localhost:8000/stream/training-session?target_id=0") as ws:
        training_data = []
        async for binary_data in ws:
            message = msgpack.unpackb(binary_data, raw=False)
            packet = message['data']
            
            spikes = packet['spikes']['spike_counts']
            target = (packet['intention']['target_x'], packet['intention']['target_y'])
            
            training_data.append({'spikes': spikes, 'target': target})
            
            if len(training_data) >= 1000:
                break
        
        # Train your decoder
        decoder.fit(training_data)

asyncio.run(train_decoder())
```

### 2. Ground Truth Validation

Validate decoder predictions against actual targets:

```python
import numpy as np

async def validate_decoder(decoder):
    errors = []
    async with websockets.connect("ws://localhost:8000/stream/validation") as ws:
        async for binary_data in ws:
            message = msgpack.unpackb(binary_data, raw=False)
            packet = message['data']
            
            predicted = decoder.predict(packet['spikes']['spike_counts'])
            actual = (packet['intention']['target_x'], packet['intention']['target_y'])
            
            error = np.linalg.norm(np.array(predicted) - np.array(actual))
            errors.append(error)
            
            if len(errors) >= 500:
                break
    
    print(f"Mean Error: {np.mean(errors):.2f}mm")
    print(f"Std Error: {np.std(errors):.2f}mm")
```

### 3. Multi-User Calibration

Independent sessions for team calibration:

```python
import requests

users = ['alice', 'bob', 'charlie']
for user in users:
    response = requests.post(
        'http://localhost:8000/api/sessions/create',
        json={'custom_code': f'calibration-{user}'}
    )
    print(f"{user}: {response.json()['stream_url']}")

# Each user streams independently
requests.post('http://localhost:8000/api/control/calibration-alice/pause')
# Bob and Charlie's streams continue unaffected
```

### 4. Calibration Workflow

Build target-specific calibration datasets:

```python
# Get all trials for target 0
response = requests.get('http://localhost:8000/api/trials/by-target/0')
trials = response.json()['trials']  # e.g., 77 trials

# Stream data from each calibration trial
for trial in trials[:10]:
    trial_id = trial['trial_id']
    stream_url = f"ws://localhost:8000/stream/calib?trial_id={trial_id}"
    # Connect and collect calibration data
```

## Limitations

**Timing:**
- Soft real-time only (1-15ms jitter, OS scheduler dependent)
- Not suitable for safety-critical closed-loop control (<100μs requirements)
- Windows: 10-15ms jitter, Linux: 1-5ms (depends on CONFIG_HZ)

**Dataset:**
- MC_Maze dataset only (hardcoded NWB schema)
- Field names: `cursor_pos`, `hand_vel`, `active_target`

**Scalability:**
- Max 10 concurrent sessions (configurable)
- Performance degradation with >7 sessions
- ThreadPool: hardcoded 4 workers ([data_loader.py:54](src/phantomlink/data_loader.py#L54))

**I/O Bottlenecks:**
- HDF5 memory-mapped reads: ~5-10ms per packet on SSD
- Random access patterns cause seek overhead

## Testing

### Quick Test

```bash
pytest -v
pytest --cov=. --cov-report=html
```

### Stream Validation

```bash
# MessagePack client (recommended)
python examples/msgpack_client_example.py

# LSL streaming test
python examples/lsl_client_example.py

# Legacy JSON client (10 seconds, 400 packets expected)
python test_client.py 10

# View sample packets
python test_client.py sample
```

### Specialized Tests

```bash
# Multi-session isolation
python test_multi_session.py

# Calibration API
python test_calibration.py

# Filter by target
python test_calibration.py target 0

# Filter by trial
python test_calibration.py trial 5

# Noise injection demo
python examples/noise_injection_demo.py
```

### Expected Output

```
=== Stream Metadata ===
  dataset: MC_Maze
  total_packets: 11748
  frequency_hz: 40
  num_channels: 142

=== Validation Results ===
  packets_received: 400
  elapsed_seconds: 10.002
  actual_rate_hz: 39.99
  interval_mean_ms: 25.005
  interval_std_ms: 0.523
  sequence_gaps: 0

=== Timing Analysis ===
  ✓ Interval timing: PASS (25.01ms ≈ 25ms)
  ✓ Stream rate: PASS (39.99Hz ≈ 40Hz)
  ✓ Sequence integrity: PASS (no gaps)
```

## Development

### Project Structure

```
PhantomLink/
├── src/phantomlink/
│   ├── server.py           # FastAPI app
│   ├── session_manager.py  # Session orchestration
│   ├── playback_engine.py  # 40Hz streaming
│   ├── lsl_streamer.py     # LSL outlets
│   ├── data_loader.py      # NWB/HDF5 loader
│   ├── models.py           # Data models
│   └── config.py           # Configuration
├── tests/                  # Test suite
├── examples/               # Client examples
├── data/                   # mc_maze.nwb
└── main.py                # Entry point
```

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov  # dev dependencies
```

### Code Guidelines

- Type hints on all functions
- Async/await for all I/O operations
- Use `logger.info/warning/error` for diagnostics
- Fail fast, propagate errors clearly
- No mock data - single source of truth from NWB files
- Docstrings for public functions

### Testing

```bash
pytest -v
pytest --cov=. --cov-report=html
```

## Troubleshooting

**Port in use:**
```bash
set PHANTOM_PORT=8001  # Windows
python main.py
```

**Dataset not found:**
```bash
dir data\raw\mc_maze.nwb  # Verify file exists
```

**Low stream rate:**
- Check server logs
- Use SSD (not HDD)
- Monitor CPU usage

**Session errors:**
```bash
curl -X POST http://localhost:8000/api/sessions/cleanup
```

## Resources

- [Beginner's Guide to BCIs](docs/BEGINNERS_GUIDE.md) - Educational introduction
- [Noise Injection Guide](docs/NOISE_INJECTION_GUIDE.md) - Robustness testing
- [Data Analysis Notebook](notebooks/data_analysis.ipynb) - Dataset exploration
- [Neural Latents Benchmark](https://neurallatents.github.io/) - MC_Maze dataset source
- [DANDI Archive #000140](https://dandiarchive.org/dandiset/000140) - Dataset download
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

Research use only. MC_Maze dataset from Neural Latents Benchmark.

## Contact

- GitHub: [@yelabb](https://github.com/yelabb)
- Project: [PhantomLink](https://github.com/yelabb/PhantomLink)
- Issues: [Report a bug](https://github.com/yelabb/PhantomLink/issues)
