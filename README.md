<div align="center">

# 🧠 PhantomLink

### Real-Time Neural Data Streaming Server for BCI Development

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-Research-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-MVP_Complete-success.svg)](https://github.com/yelabb/PhantomLink)
[![Data Analysis](https://img.shields.io/badge/📊_Data_Analysis-Notebook-orange.svg)](notebooks/data_analysis.ipynb)
[![Beginner's Guide](https://img.shields.io/badge/📚_Beginner's_Guide-Learn-blue.svg)](docs/BEGINNERS_GUIDE.md)

**The Ethereal/Mailtrap for Neurotechnology**

*Stream pre-recorded neural data at 40Hz with millisecond-range timing, simulating live brain-computer interface signals for decoder development, calibration workflows, and ground truth validation.*

> ⚠️ **Timing Disclaimer:** PhantomLink provides soft real-time streaming (1-15ms jitter) suitable for algorithm development and testing. For safety-critical applications requiring hard real-time guarantees (<100μs), use dedicated real-time OS and hardware.

> **New to Brain-Computer Interfaces?** Check out our [Complete Beginner's Guide](docs/BEGINNERS_GUIDE.md) for an educational introduction to BCIs, neural data, and how PhantomLink works!

[Quick Start](#-quick-start) • [Features](#-features) • [API Documentation](#-api-reference) • [Architecture](#-architecture) • [Contributing](#-contributing) • [📚 Beginner's Guide](docs/BEGINNERS_GUIDE.md)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Reference](#-api-reference)
- [Use Cases](#-use-cases)
- [Development](#-development)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**PhantomLink** is a high-performance neural data streaming server designed for brain-computer interface (BCI) research and development. It replays real neural recordings from the MC_Maze dataset at 40Hz with strict 25ms timing intervals, enabling developers to:

- **Develop BCI Decoders**: Train and test decoding algorithms with real neural data
- **Calibration Workflows**: Filter streams by target intention or trial ID for decoder calibration
- **Multi-User Testing**: Isolate independent sessions with shareable URLs (ChatGPT-style architecture)
- **Ground Truth Validation**: Validate decoder predictions against actual target positions
- **Performance Benchmarking**: Test decoder throughput and latency under realistic conditions

### What Makes PhantomLink Special?

- 🎯 **Real Neural Data**: Uses MC_Maze dataset (142 neural units, 294s, 100 trials) from the Neural Latents Benchmark
- ⚡ **40Hz Streaming**: Millisecond-range timing (1-15ms jitter) for realistic BCI simulation
- 🔄 **Multi-Session Isolation**: Each user/experiment gets independent playback state
- 🎚️ **Intent-Based Filtering**: Stream only packets matching specific targets or trials
- 🚀 **Production-Ready**: FastAPI + Uvicorn ASGI with async WebSocket streaming
- 💾 **Memory Efficient**: Lazy-loaded NWB/HDF5 with memory-mapped access

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **40Hz Real-Time Streaming** | WebSocket + LSL endpoints with soft real-time timing (1-15ms variance) |
| **MessagePack Binary Protocol** | 60% bandwidth reduction + 3-5x faster serialization vs JSON |
| **Dual Streaming Protocols** | WebSocket for web clients + LSL for neuroscience tools (OpenViBE, BCI2000) |
| **Multi-Session Architecture** | Independent streams with shareable URLs and automatic expiration |
| **Intent-Based Calibration** | Query trials by target, filter streams by intention |
| **Time-Aligned Payloads** | Spike counts + cursor kinematics + target intention synchronized to 25ms bins |
| **REST Control API** | Pause/resume/seek controls per session |
| **Trial Metadata API** | Query 100 trials with target positions and timing markers |
| **Lazy Loading** | Memory-mapped HDF5 access, no RAM bottleneck |
| **Built-in Validation** | Stream integrity testing and performance metrics |
| **🎯 Realistic Noise Injection** | Stress-test mode with Gaussian noise + non-stationary drift for production robustness |

### 🎯 Stress-Testing Mode (NEW!)

**Problem**: Decoders trained on clean data fail in production due to neural noise, drift, and implant micro-movements.

**Solution**: `NoiseInjectionMiddleware` transforms PhantomLink from a "playback tool" into a **stress-test simulator** by injecting:

1. **Gaussian White Noise**: Realistic firing rate variability
2. **Non-Stationary Drift**: Simulates neural fatigue and implant movement (slow + fast components)

```python
from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware

# Configure stress-test mode
middleware = NoiseInjectionMiddleware(
    noise_std=0.5,              # Moderate Gaussian noise
    drift_amplitude=0.3,         # 30% drift amplitude
    drift_period_seconds=60.0,   # Neural fatigue over 60s
    enable_noise=True,
    enable_drift=True
)

# Create engine with stress-testing
engine = PlaybackEngine(data_path, noise_middleware=middleware)
```

**Stress Levels**:
- **Light**: `noise_std=0.2, drift_amplitude=0.1` - Minimal impairment
- **Moderate**: `noise_std=0.5, drift_amplitude=0.3` - Realistic production conditions
- **Intense**: `noise_std=1.0, drift_amplitude=0.5` - Challenging scenarios
- **Extreme**: `noise_std=2.0, drift_amplitude=0.8` - Stress-test limits

**Use Cases**:
- 🔬 **Robustness Testing**: Validate decoder performance under realistic noise
- 🏋️ **Stress-Testing**: Push algorithms to failure boundaries
- 📊 **Comparative Analysis**: Benchmark decoders with/without noise
- 🎓 **Training Augmentation**: Train decoders on noisy data for better generalization

See [examples/noise_injection_demo.py](examples/noise_injection_demo.py) for complete examples and visualizations.

### Data Stream Format

**MessagePack Binary Protocol** (60% smaller, 3-5x faster than JSON):

Each 40Hz packet contains:
- **Spike Counts**: 142 neural channels (int32 array)
- **Kinematics**: Cursor position (x, y) and velocity (vx, vy)
- **Intention**: Target ID, position, and distance
- **Metadata**: Trial ID, timestamp, sequence number

```python
# Example MessagePack deserialization (Python)
import msgpack
import websockets

async with websockets.connect("ws://localhost:8000/stream/swift-neural-42") as ws:
    binary_data = await ws.recv()
    packet = msgpack.unpackb(binary_data, raw=False)
    
    # Access data
    spike_counts = packet["data"]["spikes"]["spike_counts"]  # 142 channels
    kinematics = packet["data"]["kinematics"]  # {x, y, vx, vy}
    intention = packet["data"]["intention"]    # {target_id, target_x, target_y}
```

**Performance Gains (142 channels @ 40Hz)**:
- JSON: ~15KB/packet → MessagePack: ~6KB/packet (60% reduction)
- Serialization: 3-5x faster CPU overhead
- Bandwidth: 600KB/s → 240KB/s for 40Hz stream

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **~2GB disk space** for neural dataset
- **Internet connection** for dataset download

### Installation

```bash
# Clone the repository
git clone https://github.com/yelabb/PhantomLink.git
cd PhantomLink

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Download Dataset

PhantomLink uses the MC_Maze dataset from the [DANDI Archive #000140](https://dandiarchive.org/dandiset/000140):

```bash
# Install DANDI CLI (if not already installed)
pip install dandi

# Download MC_Maze dataset
dandi download https://dandiarchive.org/dandiset/000140/draft

# Move to data directory
mkdir data
mv 000140/sub-Jenkins/* data/mc_maze.nwb
```

**Expected file location**: `data/mc_maze.nwb` (~1.5GB)

### Start Server

```bash
python main.py
```

You should see:

```
INFO - Starting PhantomLink Core server
INFO - Using NWB dataset: data\mc_maze.nwb
INFO - Initializing shared data loader: data\mc_maze.nwb
INFO - Found 142 neural units
INFO - Found 100 trials
INFO - Shared loader ready: 142 channels, 293.7s, 100 trials
INFO - Server ready on 0.0.0.0:8000
INFO - Session-based isolation enabled (max 10 sessions)
INFO - Uvicorn running on http://0.0.0.0:8000
```

🎉 **Server is running!** Visit `http://localhost:8000/docs` for interactive API documentation.

### Test the Stream

```bash
# Validate 40Hz streaming (10 seconds, 400 packets expected)
python test_client.py 10

# Test multi-session isolation
python test_multi_session.py

# Test calibration API
python test_calibration.py
```

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    PhantomLink Server                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────────────────────┐    │
│  │   FastAPI    │◄────►│    Session Manager           │    │
│  │   Server     │      │  - Multi-session isolation   │    │
│  │              │      │  - LRU eviction              │    │
│  │  REST + WS   │      │  - Auto-cleanup (1hr TTL)    │    │
│  └──────────────┘      └──────────────────────────────┘    │
│         ▲                          │                         │
│         │                          ▼                         │
│         │              ┌──────────────────────┐             │
│    Client Requests     │  Playback Engine(s)  │             │
│                        │  - 40Hz async loop   │             │
│                        │  - Pause/resume/seek │             │
│                        │  - Intent filtering  │             │
│                        └──────────────────────┘             │
│                                   │                          │
│                                   ▼                          │
│                        ┌──────────────────────┐             │
│                        │    Data Loader       │             │
│                        │  - Lazy NWB/HDF5     │             │
│                        │  - Memory-mapped     │             │
│                        │  - Trial metadata    │             │
│                        └──────────────────────┘             │
│                                   │                          │
└───────────────────────────────────┼──────────────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │   mc_maze.nwb        │
                         │   (142 units, 294s)  │
                         └──────────────────────┘
```

### Core Components

| Component | Responsibility |
|-----------|----------------|
| **server.py** | FastAPI app with REST + WebSocket endpoints, session management |
| **session_manager.py** | Multi-session orchestration, LRU eviction, auto-cleanup |
| **playback_engine.py** | 40Hz asyncio streaming loop with intent filtering |
| **lsl_streamer.py** | LSL (Lab Streaming Layer) outlet manager for neuroscience tools |
| **data_loader.py** | Lazy NWB/HDF5 loader with trial metadata extraction |
| **models.py** | Pydantic data models for type safety and validation |
| **config.py** | Configuration settings (frequency, ports, limits) |

### Technology Stack

- **Web Framework**: FastAPI 0.109+ with Uvicorn ASGI server
- **Neural Data**: PyNWB 2.6+ with H5py for lazy HDF5 access
- **Streaming Protocols**: WebSockets 12.0 + pylsl 1.16+ for dual streaming
- **Async Runtime**: Python asyncio for concurrent streaming
- **Data Models**: Pydantic 2.5+ for type validation

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Packet Generation | ~7ms (HDF5 read + binning) |
| Serialization | MessagePack: 3-5x faster than JSON |
| Payload Size | ~6KB/packet (60% smaller than JSON) |
| Bandwidth | 240KB/s @ 40Hz (vs 600KB/s with JSON) |
| Timing Precision | 1-15ms variance (soft real-time, OS-dependent) |
| Memory Footprint | <500MB (memory-mapped, shared across sessions) |
| Sustained Throughput | 40Hz target rate per session |
| Latency | 25ms ± 5-15ms per packet (asyncio + OS scheduler) |
| Session Overhead | ~50KB per session |
| Max Concurrent Sessions | 10 (configurable, LRU eviction) |
| Session TTL | 3600s (1 hour, auto-cleanup) |

---

## 📡 API Reference

### Health Check

Check server status:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "timestamp": "2026-01-12T13:30:00Z"
}
```

### Session Management

#### Create Session

Create a new isolated session with auto-generated or custom code:

```bash
# Auto-generated code (e.g., "swift-neural-42")
curl -X POST http://localhost:8000/api/sessions/create

# Custom code
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"custom_code": "my-experiment-1"}'
```

Response:
```json
{
  "session_code": "swift-neural-42",
  "stream_url": "ws://localhost:8000/stream/swift-neural-42",
  "created_at": "2026-01-12T13:30:00Z"
}
```

#### List Sessions

Get all active sessions with statistics:

```bash
curl http://localhost:8000/api/sessions
```

Response:
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

### LSL (Lab Streaming Layer) Streaming

PhantomLink automatically creates LSL outlets for each session, enabling integration with neuroscience tools like OpenViBE, BCI2000, and MATLAB.

#### LSL Stream Names

For each session (e.g., `swift-neural-42`), three LSL streams are created:

- **PhantomLink-Neural-{session_code}**: Spike counts (142 channels, int32)
- **PhantomLink-Kinematics-{session_code}**: Cursor position and velocity (4 channels: vx, vy, x, y)
- **PhantomLink-Intention-{session_code}**: Target and trial markers (4 channels: target_id, target_x, target_y, trial_id)

#### Python LSL Client Example

```python
from pylsl import StreamInlet, resolve_stream

# Resolve the neural stream
print("Looking for PhantomLink-Neural stream...")
streams = resolve_stream('type', 'EEG')

# Connect to the stream
inlet = StreamInlet(streams[0])

# Receive data at 40Hz
while True:
    sample, timestamp = inlet.pull_sample()
    print(f"LSL Timestamp: {timestamp:.3f}, Spike counts: {sample[:5]}...")  # First 5 channels
```

#### Configuration

LSL can be enabled/disabled via environment variables:

```bash
# Disable LSL (WebSocket only)
export PHANTOM_LSL_ENABLED=false

# Customize LSL stream names
export PHANTOM_LSL_STREAM_NAME="MyBCI-Stream"
export PHANTOM_LSL_SOURCE_ID="MyBCI-001"
```

#### Filter by Target

Stream only packets reaching for a specific target:

```bash
ws://localhost:8000/stream/swift-neural-42?target_id=0
```

#### Filter by Trial

Stream only packets from a specific trial:

```bash
ws://localhost:8000/stream/swift-neural-42?trial_id=42
```

### Playback Control

Control playback for each session independently:

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

Response:
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

Response:
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
    },
    ...
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

---

## 💡 Use Cases

### 1. Multi-User Calibration Sessions

Share independent calibration sessions with team members:

```python
import requests

# Team lead creates sessions for each user
users = ['alice', 'bob', 'charlie']
for user in users:
    response = requests.post(
        'http://localhost:8000/api/sessions/create',
        json={'custom_code': f'calibration-{user}'}
    )
    print(f"{user}: {response.json()['stream_url']}")

# Output:
# alice: ws://localhost:8000/stream/calibration-alice
# bob: ws://localhost:8000/stream/calibration-bob
# charlie: ws://localhost:8000/stream/calibration-charlie

# Each user streams independently
requests.post('http://localhost:8000/api/control/calibration-alice/pause')
# Bob and Charlie's streams continue unaffected
```

### 2. BCI Decoder Training

Train decoders with real neural data and known intentions:

```python
import websockets
import msgpack  # pip install msgpack
import asyncio

async def train_decoder():
    # Create dedicated training session
    response = requests.post(
        'http://localhost:8000/api/sessions/create',
        json={'custom_code': 'decoder-training-v1'}
    )
    stream_url = response.json()['stream_url']
    
    # Connect and collect training data with MessagePack
    async with websockets.connect(f'{stream_url}?target_id=0') as ws:
        training_data = []
        async for binary_data in ws:
            # Deserialize MessagePack (3-5x faster than JSON)
            message = msgpack.unpackb(binary_data, raw=False)
            packet = message['data']
            
            # Extract features
            spikes = packet['spikes']['spike_counts']
            target = (packet['intention']['target_x'], 
                     packet['intention']['target_y'])
            
            # Collect training examples
            training_data.append({'spikes': spikes, 'target': target})
            
            if len(training_data) >= 1000:
                break
        
        # Train your decoder
        decoder.fit(training_data)

asyncio.run(train_decoder())
        decoder.fit(training_data)

asyncio.run(train_decoder())
```

### 3. Ground Truth Validation

Validate decoder predictions against actual targets:

```python
import websockets
import msgpack
import asyncio
import numpy as np

async def validate_decoder(decoder):
    response = requests.post(
        'http://localhost:8000/api/sessions/create',
        json={'custom_code': 'validation-run1'}
    )
    stream_url = response.json()['stream_url']
    
    errors = []
    async with websockets.connect(stream_url) as ws:
        async for binary_data in ws:
            # Deserialize MessagePack
            message = msgpack.unpackb(binary_data, raw=False)
            packet = message['data']
            
            # Decoder prediction
            predicted = decoder.predict(packet['spikes']['spike_counts'])
            
            # Ground truth
            actual = (packet['intention']['target_x'],
                     packet['intention']['target_y'])
            
            # Calculate error
            error = np.linalg.norm(np.array(predicted) - np.array(actual))
            errors.append(error)
            
            if len(errors) >= 500:
                break
    
    print(f"Mean Error: {np.mean(errors):.2f}mm")
    print(f"Std Error: {np.std(errors):.2f}mm")

asyncio.run(validate_decoder(my_decoder))
```

### 4. Calibration Workflow

Build calibration datasets with specific targets:

```python
import requests

# Get all trials reaching for target 0
response = requests.get('http://localhost:8000/api/trials/by-target/0')
trials = response.json()['trials']  # 77 trials

# Create session for calibration
session = requests.post(
    'http://localhost:8000/api/sessions/create',
    json={'custom_code': 'calibration-target0'}
).json()

# Stream data from each calibration trial
for trial in trials[:10]:  # First 10 trials
    trial_id = trial['trial_id']
    stream_url = f"{session['stream_url']}?trial_id={trial_id}"
    # Connect to stream_url and collect calibration data
```

---

## ⚠️ Technical Limitations & Known Issues

### Timing & Real-Time Performance

**Soft Real-Time Only (Not Hard Real-Time)**
- PhantomLink uses `asyncio.sleep()` which relies on OS scheduler
- **Actual jitter:** 1-15ms (Windows: 10-15ms, Linux: 1-5ms depending on CONFIG_HZ)
- **NOT suitable for:** Safety-critical motor control, closed-loop stimulation with <1ms latency requirements
- **Suitable for:** Algorithm development, decoder training, prototyping, ground truth validation

**OS-Specific Timing Characteristics:**
| OS | Typical Jitter | Scheduler Resolution |
|----|---------------|---------------------|
| Windows 10/11 | 10-15ms | ~15.6ms (64Hz timer) |
| Linux (CONFIG_HZ=1000) | 1-4ms | 1ms |
| Linux (CONFIG_HZ=250) | 4-8ms | 4ms |
| macOS | 5-10ms | Variable |

**For Hard Real-Time (if needed):**
- Use PREEMPT_RT patched Linux kernel
- Replace `asyncio.sleep()` with busy-wait loops for last microseconds
- Consider dedicated real-time hardware (e.g., NI DAQ, Intan RHS)

### I/O & Concurrency Bottlenecks

**ThreadPool Executor: Hardcoded 4 Workers**
- Located in [data_loader.py:54](src/phantomlink/data_loader.py#L54): `ThreadPoolExecutor(max_workers=4)`
- **Impact:** With 10 concurrent sessions, threads are shared causing I/O contention
- **Estimated latency:** 25ms (ideal) → 50-200ms (10 sessions)
- **Recommendation:** Make configurable based on CPU cores or session count

**Disk I/O Performance:**
- HDF5 memory-mapped reads: ~5-10ms per packet on SSD
- **Bottleneck:** Random access patterns cause SSD seek overhead
- **Solution:** Sequential pre-buffering (not yet implemented)

### Dataset Format Coupling

**NWB Schema Hardcoded for MC_Maze**
- Field names hardcoded: `cursor_pos`, `hand_vel`, `active_target`
- **Fragility:** If NWB structure changes (common in research), loader breaks
- **Current datasets supported:** MC_Maze from Neural Latents Benchmark only

**Proposed Solution (Future Enhancement):**
```python
# config.py
class DatasetSchema(BaseSettings):
    cursor_field: str = "cursor_pos"
    velocity_field: str = "hand_vel"
    target_field: str = "active_target"
```

### Scalability Constraints

**Session Limits:**
- Max concurrent sessions: 10 (configurable in [config.py](src/phantomlink/config.py))
- LRU eviction when limit exceeded
- Each session: ~50KB memory overhead

**Performance Degradation:**
| Concurrent Sessions | Avg Latency | Timing Jitter |
|---------------------|-------------|---------------|
| 1-3 sessions | 25-30ms | ±2-5ms |
| 4-7 sessions | 30-50ms | ±5-10ms |
| 8-10 sessions | 50-100ms | ±10-20ms |
| >10 sessions | >100ms | ±20-50ms |

### Use Case Recommendations

| Use Case | PhantomLink Suitable? | Alternatives |
|----------|----------------------|--------------|
| **Algorithm Development** | ✅ Excellent | - |
| **Decoder Training** | ✅ Excellent | - |
| **Ground Truth Validation** | ✅ Good | - |
| **Closed-Loop BCI (soft RT)** | ⚠️ Testing only | Real hardware |
| **Safety-Critical Control** | ❌ Not suitable | Real-time OS + hardware |
| **High-Throughput (>100Hz)** | ❌ Not designed for | Custom C++/Rust solution |
| **Multi-User Demos (<5 users)** | ✅ Good | - |
| **Production Scale (>10 users)** | ⚠️ Limited | Load balancer + multiple instances |

---

## 🛠️ Development

### Project Structure

```
PhantomLink/
├── data/                       # Neural datasets (gitignored)
│   └── mc_maze.nwb            # MC_Maze dataset (~1.5GB)
├── config.py                  # Server configuration
├── models.py                  # Pydantic data models
├── data_loader.py             # NWB/HDF5 lazy loader
├── playback_engine.py         # 40Hz streaming engine
├── session_manager.py         # Multi-session orchestration
├── server.py                  # FastAPI application
├── main.py                    # Entry point
├── test_client.py             # Stream validation
├── test_calibration.py        # Calibration API tests
├── test_multi_session.py      # Session isolation tests
├── test_*.py                  # Unit/integration tests
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata
└── README.md                  # This file
```

### Environment Setup

```bash
# Clone repository
git clone https://github.com/yelabb/PhantomLink.git
cd PhantomLink

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov
```

### Adding a New Feature

Example: Add eye-tracking data to kinematics

**1. Update data model** ([models.py](models.py)):

```python
class Kinematics(BaseModel):
    x: float
    y: float
    vx: float
    vy: float
    eye_x: float  # New field
    eye_y: float  # New field
```

**2. Extend data loader** ([data_loader.py](data_loader.py)):

```python
def get_kinematics(self, start_time, end_time):
    # ... existing code ...
    
    # Extract eye tracking data
    eye_data = self._nwb.processing['behavior']['eye_pos'].data[start_idx:end_idx]
    
    return {
        **existing_data,
        'eye_x': eye_data[:, 0],
        'eye_y': eye_data[:, 1]
    }
```

**3. Update playback engine** ([playback_engine.py](playback_engine.py)):

```python
kinematics = Kinematics(
    x=..., y=..., vx=..., vy=...,
    eye_x=float(kinematics_data['eye_x'][0]),
    eye_y=float(kinematics_data['eye_y'][0])
)
```

### Development Workflow

```bash
# 1. Make changes
# Edit source files

# 2. Run tests
pytest -v

# 3. Start server
python main.py

# 4. Test changes
python test_client.py 10

# 5. Check coverage
pytest --cov=. --cov-report=html
```

### Code Style Guidelines

- ✅ **Type Hints**: All functions use type annotations
- ✅ **Async/Await**: All I/O operations are async
- ✅ **Logging**: Use `logger.info/warning/error` for diagnostics
- ✅ **Error Handling**: Fail fast, propagate errors clearly
- ✅ **No Mock Data**: Single source of truth from NWB files
- ✅ **Documentation**: Docstrings for all public functions

---

## 🧪 Testing

PhantomLink includes comprehensive test coverage for all components.

### Quick Test Run

```bash
# Run all tests
pytest -v

# Windows batch file
test.bat
```

### Test Suites

```bash
# Unit tests only
pytest test_models.py test_data_loader.py test_playback_engine.py -v

# Integration tests
pytest test_server.py test_multi_session.py -v

# With coverage
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Manual Testing

```bash
# Test MessagePack client (recommended)
python examples/msgpack_client_example.py

# Test LSL streaming
python examples/lsl_client_example.py

# Validate 40Hz streaming (legacy JSON client)
python test_client.py 10

# View sample packets
python test_client.py sample

# Test session isolation
python test_multi_session.py

# Test calibration API
python test_calibration.py

# Filter by target
python test_calibration.py target 0

# Filter by trial
python test_calibration.py trial 5
```

### Expected Test Output

**Stream Validation**:
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

### Coverage Report

```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

---

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Change port in config.py or use environment variable
# Windows
set PHANTOM_PORT=8001

# Linux/macOS
export PHANTOM_PORT=8001

# Then restart server
python main.py
```

#### Dataset Not Found

```bash
# Verify file exists
# Windows
dir data\mc_maze.nwb

# Linux/macOS
ls data/mc_maze.nwb

# Re-download if missing
dandi download https://dandiarchive.org/dandiset/000140/draft
```

#### Low Stream Rate (<40Hz)

- Check server logs for timing errors
- Verify NWB file is on SSD (not HDD)
- Ensure no other processes are accessing the file
- Check CPU usage (should be <10% per core)

```bash
# Get performance stats
curl http://localhost:8000/api/stats/{session_code}
```

#### Connection Refused

```bash
# Test health endpoint
curl http://localhost:8000/health

# List active sessions
curl http://localhost:8000/api/sessions

# Try 127.0.0.1 instead of localhost
ws://127.0.0.1:8000/stream/my-session
```

#### Session Not Found

```bash
# Create session explicitly
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"custom_code": "my-session"}'

# Or let WebSocket auto-create on connect
ws://localhost:8000/stream/my-session
```

#### Too Many Sessions

```bash
# Delete unused sessions
curl -X DELETE http://localhost:8000/api/sessions/{session_code}

# Trigger cleanup of expired sessions
curl -X POST http://localhost:8000/api/sessions/cleanup
```

### Performance Tuning

**Check current performance:**
```bash
curl http://localhost:8000/api/stats/{session_code}
```

**Optimize for higher throughput:**
- Use SSD storage for NWB file
- Close unnecessary background applications
- Increase process priority
- Monitor CPU usage

### Debug Mode

Enable verbose logging in [config.py](config.py):

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🤝 Contributing

We welcome contributions from the BCI and neurotechnology community!

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with tests and documentation
4. **Run tests**: `pytest -v`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines

- Write tests for new features
- Update documentation
- Follow existing code style
- Add type hints
- Use async/await for I/O operations
- Keep functions focused and testable

### Reporting Issues

Found a bug or have a feature request?

1. Check existing issues first
2. Provide detailed description
3. Include server logs if relevant
4. Share test output from `python test_client.py 10`

---

## 📚 Additional Resources

- **Dataset**: [Neural Latents Benchmark](https://neurallatents.github.io/)
- **DANDI Archive**: [Dataset #000140](https://dandiarchive.org/dandiset/000140)
- **PyNWB Documentation**: [pynwb.readthedocs.io](https://pynwb.readthedocs.io/)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)

---

## 📄 License

This project is for **research use only**. The MC_Maze dataset is provided by the [Neural Latents Benchmark](https://neurallatents.github.io/) project.

---

## 🗺️ Roadmap

### Phase 2: Frontend Dashboard
- [ ] Real-time spike raster visualization
- [ ] Cursor trajectory plotting
- [ ] Decoder performance metrics
- [ ] Session management UI

### Phase 3: Decoder Integration
- [ ] Kalman filter decoder implementation
- [ ] Online calibration endpoint
- [ ] Ground truth comparison metrics
- [ ] A/B testing framework

### Phase 4: Multi-Dataset Support
- [ ] Switch between different NWB files
- [ ] Dataset selection API per session
- [ ] Unified metadata format
- [ ] Recording mode for saving streams

---

## 📞 Contact

- **GitHub**: [@yelabb](https://github.com/yelabb)
- **Project**: [PhantomLink](https://github.com/yelabb/PhantomLink)
- **Issues**: [Report a bug](https://github.com/yelabb/PhantomLink/issues)

---

<div align="center">

**Built with ❤️ for the BCI Community**

*Last Updated: January 12, 2026 • Version 0.2.0 • Status: ✅ MVP Complete*

[⬆ Back to Top](#-phantomlink)

</div>
