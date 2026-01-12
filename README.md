# PhantomLink Core

> **📖 Single Source of Truth**: This README is the authoritative documentation. All other docs redirect here.

**The Ethereal/Mailtrap for Neurotechnology** 🧠⚡

PhantomLink Core streams pre-recorded neural data from the MC_Maze dataset at 40Hz with strict 25ms timing, simulating a live BCI feed from a neural implant. Each packet delivers time-aligned spike counts + cursor kinematics + target intention for decoder development and testing.

## Architecture

- **Single-Stack Python**: FastAPI + Uvicorn ASGI server
- **Native NWB/HDF5**: Direct pynwb integration with lazy memory-mapped access
- **Strict 40Hz Streaming**: Asyncio-based playback maintains precise 25ms intervals
- **Real Neural Data**: MC_Maze dataset from Neural Latents Benchmark (142 units, 294s duration, 100 trials)
- **Calibration-Ready**: Intent-based filtering for decoder validation workflows

## Features

✅ **40Hz Real-Time Streaming** - WebSocket endpoint with sub-millisecond timing accuracy  
✅ **Multi-Session Isolation** - Independent streams with shareable URLs (ChatGPT-style)  
✅ **Intent-Based Calibration API** - Query trials by target, filter streams by intention  
✅ **Lazy Loading** - Memory-mapped HDF5 access, no RAM bottleneck  
✅ **Time-Aligned Payloads** - Spike counts + cursor kinematics synchronized to 25ms bins  
✅ **Real Trial Data** - 100 trials with target positions and timing markers  
✅ **REST API** - Control endpoints for pause/resume/seek + trial queries  
✅ **Validation Client** - Built-in stream integrity testing

## Quick Start

**Prerequisites**: Python 3.12+, ~2GB disk space for dataset


## Quick Start

**Prerequisites**: Python 3.12+, ~2GB disk space for dataset

### 1. Setup Environment

```bash
# Clone/navigate to project
cd PhantomLink

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Dataset

Download the MC_Maze Small dataset from [DANDI Archive #000140](https://dandiarchive.org/dandiset/000140):

```bash
# Install dandi-cli (if not in requirements)
pip install dandi

# Download MC_Maze Small dataset
dandi download https://dandiarchive.org/dandiset/000140/draft
# or download manually and place as data/mc_maze.nwb
```

**Expected file**: `data/mc_maze.nwb` (~1.5GB)

### 3. Start Server

```bash
python main.py
```

Expected output:
```
INFO - Starting PhantomLink Core server
INFO - Using NWB dataset: data\mc_maze.nwb
INFO - Initializing shared data loader: data\mc_maze.nwb
INFO - Opened NWB file: data\mc_maze.nwb
INFO - Found 142 neural units
INFO - Found processing module: behavior
INFO -   - cursor_pos: (287710, 2), sampling rate: 1000.0Hz
INFO -   - hand_vel: (287710, 2)
INFO - Found 100 trials
INFO - Shared loader ready: 142 channels, 293.7s, 100 trials
INFO - Server ready on 0.0.0.0:8000
INFO - Session-based isolation enabled (max 10 sessions)
INFO - Uvicorn running on http://0.0.0.0:8000
```

Server is now ready for multi-session streaming!

## Testing the Stream

### Test Multi-Session Architecture

Test session isolation and concurrent streaming:

```bash
python test_multi_session.py
```

Expected output:
```
=== PhantomLink Multi-Session Test Suite ===

[1/4] Creating session...
✓ Created session: neural-link-18
  Stream URL: ws://localhost:8000/stream/neural-link-18

[2/4] Listing sessions...
=== Active Sessions (1) ===
Session: neural-link-18
  Age: 3s | Idle: 3s | Connections: 0
  Running: False | Position: packet 0

[3/4] Testing stream from session...
✓ Received 201 packets in 5s (40.1 Hz)

[4/4] Testing session isolation...
✓ Paused session1, session2 streams independently
✓ Sessions are isolated
```

### Validate 40Hz Integrity

Test stream for 10 seconds (400 packets expected):

```bash
python test_client.py 10
```

Expected output:
```
=== Stream Metadata ===
  dataset: MC_Maze
  total_packets: 287710
  frequency_hz: 40
  num_channels: 142
  duration_seconds: 7192.75

  40 packets | 1.0s | 40.0 Hz

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

### View Sample Packets

```bash
python test_client.py sample
```

Displays metadata + 3 example packets with full data structure.

### Test Calibration API

Test intent-based filtering for decoder calibration:

```bash
# Test trial/intention REST API
python test_calibration.py

# Stream only packets reaching for target 0
python test_calibration.py target 0

# Stream only packets from trial 5
python test_calibration.py trial 5
```

Expected output:
```
=== Testing Trial/Intention API ===
1. Fetching all trials...
   Found 100 trials
   Sample trial: {...}

3. Fetching all trials reaching for target 0...
   Found 77 trials reaching for target 0

=== Testing Filtered Stream (target_id=0) ===
Connected! Receiving filtered stream...
  200 packets | trial_id=1 | target=(-77, 82)

=== Results ===
Packets received: 201
Unique target positions: 2
  Target 0: (-118, -83)
  Target 1: (-77, 82)
```

## API Reference

### Session Management

PhantomLink uses **session-based isolation** - each session gets its own independent playback state with a shareable URL (similar to ChatGPT conversations). Sessions auto-expire after 1 hour of inactivity.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions/create` | POST | Create new session with optional custom code |
| `/api/sessions` | GET | List all active sessions with stats |
| `/api/sessions/{session_code}` | GET | Get specific session details |
| `/api/sessions/{session_code}` | DELETE | Delete a session |
| `/api/sessions/cleanup` | POST | Manually trigger expired session cleanup |

**Create Session Example:**
```bash
# Auto-generated code (e.g., "swift-neural-42")
curl -X POST http://localhost:8000/api/sessions/create

# Custom code
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"custom_code": "my-experiment-1"}'

# Response
{
  "session_code": "swift-neural-42",
  "stream_url": "ws://localhost:8000/stream/swift-neural-42",
  "created_at": "2026-01-12T13:30:00Z"
}
```

**List Sessions Example:**
```bash
curl http://localhost:8000/api/sessions

# Response
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
  "stats": {
    "total_sessions": 3,
    "max_sessions": 10,
    "session_ttl": 3600,
    "active_connections": 5,
    "running_sessions": 2
  }
}
```

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and status |
| `/health` | GET | Health check |
| `/api/metadata` | GET | Dataset metadata (channels, duration, etc.) |
| `/api/stats` | GET | Global playback statistics |
| `/api/trials` | GET | List all trials with target/intention data |
| `/api/trials/{trial_id}` | GET | Get specific trial information |
| `/api/trials/by-target/{target_index}` | GET | Get all trials reaching for a specific target |

**Session-Specific Control Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/control/{session_code}/pause` | POST | Pause playback for this session |
| `/api/control/{session_code}/resume` | POST | Resume playback for this session |
| `/api/control/{session_code}/stop` | POST | Stop playback for this session |
| `/api/control/{session_code}/seek?position_seconds=X` | POST | Seek to position in this session |
| `/api/control/{session_code}/metadata` | GET | Get session-specific metadata |
| `/api/control/{session_code}/stats` | GET | Get session-specific statistics |

### WebSocket Stream

**Endpoint**: `ws://localhost:8000/stream/{session_code}`  
**Frequency**: 40Hz (25ms intervals)  
**Protocol**: JSON packets

**Session Behavior:**
- Sessions are **auto-created** on first WebSocket connection if they don't exist
- Each session has **independent playback state** (pause one, stream from another)
- Sessions **expire after 1 hour** of inactivity (configurable)
- Maximum **10 concurrent sessions** (configurable, LRU eviction)

**Query Parameters** (optional):
- `trial_id` - Filter to only stream packets from a specific trial (0-99)
- `target_id` - Filter to only stream packets reaching for a specific target (0-2)

**Examples**:
```bash
# Auto-create session and stream all packets
ws://localhost:8000/stream/my-experiment-1

# Pre-create session with readable code
curl -X POST http://localhost:8000/api/sessions/create
# Returns: {"session_code": "swift-neural-42", ...}

# Stream from created session
ws://localhost:8000/stream/swift-neural-42

# Stream only trial 5 from session
ws://localhost:8000/stream/swift-neural-42?trial_id=5

# Stream only reaching for target 0 (77 trials)
ws://localhost:8000/stream/neural-link-18?target_id=0

# Multiple clients can connect to same session
ws://localhost:8000/stream/swift-neural-42  # Client 1
ws://localhost:8000/stream/swift-neural-42  # Client 2 (shares state)
```

## Data Format

### Stream Packet Structure

Each 40Hz packet contains time-aligned data at 25ms resolution:

```json
{
  "type": "data",
  "data": {
    "timestamp": 1736726400.123,
    "sequence_number": 42,
    "spikes": {
      "channel_ids": [0, 1, 2, ..., 141],
      "spike_counts": [2, 0, 3, 1, 0, ...],
      "bin_size_ms": 25.0
    },
    "kinematics": {
      "vx": 8.67,      // Hand velocity X (mm/s)
      "vy": -3.21,     // Hand velocity Y (mm/s)
      "x": 12.45,      // Cursor position X (mm)
      "y": -5.33       // Cursor position Y (mm)
    },
    "intention": {
      "target_id": 0,           // Active target index (0-2, from trial data)
      "target_x": -118.0,      // Actual target X position (mm, from trial)
      "target_y": -83.0        // Actual target Y position (mm, from trial)
    },
    "trial_id": 0,             // Trial identifier (0-99)
    "trial_time_ms": 1050.0    // Time within trial
  }
}
```

### Data Sources

- **Spikes**: 142 neural units from motor cortex, binned at 25ms
- **Kinematics**: Cursor position and hand velocity, sampled at 1000Hz (downsampled to 40Hz)
- **Behavioral Data**: From NWB `processing['behavior']` module
- **Trial Data**: 100 trials from NWB `trials` table with timing markers and target positions
- **Intention Ground Truth**: Real target coordinates from maze task (1-3 targets per trial)
- **Neural Recordings**: Real data from monkey Jenkins (2009), not simulated

## Architecture Deep Dive

### System Design

```
Client (WebSocket) ←→ FastAPI Server ←→ SessionManager ←→ PlaybackEngine(s) ←→ Shared DataLoader ←→ NWB File
                                              ↓                    ↓
                                        Session Isolation    40Hz Asyncio Loop
                                        (max 10, LRU)       (25ms precision)
```

**Multi-Session Architecture:**
- **Shared DataLoader**: Single memory-mapped NWB file instance (read-only, efficient)
- **Per-Session PlaybackEngine**: Independent playback state for each session
- **Session Isolation**: Pause/resume/seek in one session doesn't affect others
- **Shareable URLs**: Each session gets a unique code (e.g., `swift-neural-42`)
- **LRU Eviction**: When hitting max sessions, oldest is removed
- **TTL Cleanup**: Background task removes expired sessions every 5 minutes

### Key Components

**`session_manager.py`** - SessionManager class  
- Creates and manages multiple isolated sessions
- Generates readable session codes: `{adjective}-{noun}-{number}`
- Maintains single shared `MC_MazeLoader` instance (efficient memory-mapped access)
- Creates per-session `PlaybackEngine` instances (independent state)
- LRU eviction when hitting max_sessions limit (default: 10)
- TTL-based cleanup (default: 3600s = 1 hour)
- Background cleanup task runs every 5 minutes
- Thread-safe session access and management

**`data_loader.py`** - MC_MazeLoader class  
- Lazy-loads NWB file with pynwb + HDF5 memory mapping
- Extracts spike times (ragged arrays via VectorIndex)
- Reads behavioral data at 1000Hz, bins to 40Hz windows
- Parses trial table with target positions and timing markers
- Provides trial query methods: `get_trials()`, `get_trials_by_target()`, `get_trial_by_time()`
- No data preloading: ~7ms per packet extraction

**`playback_engine.py`** - PlaybackEngine class  
- Asyncio-based 40Hz streaming with strict timing
- Supports optional filtering by `trial_id` or `target_id`
- Tracks timing errors (logs every 1000 packets)
- Handles pause/resume/seek controls
- Generates StreamPacket objects with real trial context

**`server.py`** - FastAPI application  
- Session-based multi-client architecture (refactored from single-engine)
- Global `SessionManager` managing multiple `PlaybackEngine` instances
- WebSocket endpoint `/stream/{session_code}` with auto-session creation
- Session-specific REST control endpoints (`/api/control/{session_code}/pause`)
- Session management endpoints (create, list, delete, cleanup)
- Background cleanup task: `periodic_cleanup()` runs every 5 minutes
- Non-blocking async design with per-session connection tracking

**`models.py`** - Pydantic data models  
- StreamPacket, SpikeData, Kinematics, TargetIntention
- Type validation and serialization

### Performance Characteristics

- **Packet Generation**: ~7ms (HDF5 read + binning)
- **Timing Precision**: <1ms std deviation
- **Memory Footprint**: <500MB (memory-mapped file, shared across sessions)
- **Throughput**: 40Hz sustained for hours per session
- **Latency**: 25ms ± 0.5ms per packet
- **Session Overhead**: ~50KB per session (independent PlaybackEngine state)
- **Max Concurrent Sessions**: 10 (configurable, LRU eviction)
- **Session TTL**: 3600s (1 hour, configurable)

### Design Principles

1. **Single Source of Truth**: Real NWB data only, no mock data
2. **Lazy Evaluation**: Memory-map HDF5, extract on-demand
3. **Precise Timing**: Asyncio sleep with error tracking
4. **Type Safety**: Pydantic models for all data structures
5. **Fail Fast**: Errors propagate immediately, no silent failures
6. **Session Isolation**: Independent playback states, shareable URLs
7. **Resource Efficiency**: Shared DataLoader, per-session engines

## Development

### Project Structure

```
PhantomLink/
├── data/                    # NWB dataset files (gitignored)
│   └── mc_maze.nwb         # MC_Maze dataset (~1.5GB)
├── config.py               # Settings (40Hz, 25ms intervals)
├── models.py               # Pydantic data models
├── data_loader.py          # NWB file loader with trial parsing
├── playback_engine.py      # 40Hz streaming engine with filtering
├── session_manager.py      # Multi-session isolation manager
├── server.py               # FastAPI application with session API
├── main.py                 # Entry point
├── test_client.py          # Stream validation client
├── test_calibration.py     # Intent-based filtering tests
├── test_multi_session.py   # Multi-session isolation tests
├── investigate_nwb.py      # NWB structure exploration tool
├── requirements.txt        # Python dependencies
└── README.md              # This file (single source of truth)
```

### Requirements

- Python 3.12+
- pynwb >= 3.1.3
- h5py >= 3.15.1
- numpy >= 2.0
- FastAPI >= 0.109.0
- Uvicorn >= 0.27.0
- websockets >= 12.0

### Development Workflow

```bash
# 1. Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Run tests
python test_client.py 10

# 3. Make changes
# Edit data_loader.py, playback_engine.py, etc.

# 4. Test changes
python main.py
python test_client.py 10

# 5. Check logs
# Server logs timing errors every 1000 packets
```

### Adding Features

**Example: Add new behavioral signal**

1. Extend `models.py`:
```python
class Kinematics(BaseModel):
    vx: float
    vy: float
    x: float
    y: float
    eye_x: float  # New field
    eye_y: float  # New field
```

2. Update `data_loader.py`:
```python
def get_kinematics(self, start_time, end_time):
    # ... existing code ...
    eye_data = self._nwb.processing['behavior']['eye_pos'].data[start_idx:end_idx]
    return {**existing_data, 'eye_x': eye_data[:,0], 'eye_y': eye_data[:,1]}
```

3. Modify `playback_engine.py`:
```python
kinematics=Kinematics(
    vx=..., vy=..., x=..., y=...,
    eye_x=float(kinematics_data['eye_x'][0]),
    eye_y=float(kinematics_data['eye_y'][0])
)
```

### Code Style

- **No mock data**: Single source of truth from NWB files
- **Type hints**: All functions use type annotations
- **Logging**: Use `logger.info/warning/error` for diagnostics
- **Error handling**: Fail fast, propagate errors clearly
- **Async/await**: All I/O operations are async

## Use Cases

### 1. Multi-User Calibration Sessions
Share independent calibration sessions with team members:

```python
import requests
import websockets
import json

# Team lead creates sessions for each user
sessions = []
for user in ['alice', 'bob', 'charlie']:
    response = requests.post('http://localhost:8000/api/sessions/create',
                            json={'custom_code': f'calibration-{user}'})
    sessions.append(response.json())
    print(f"{user}: {response.json()['stream_url']}")

# Each user gets their own independent stream
# alice: ws://localhost:8000/stream/calibration-alice
# bob: ws://localhost:8000/stream/calibration-bob
# charlie: ws://localhost:8000/stream/calibration-charlie

# Users can pause/resume independently
requests.post('http://localhost:8000/api/control/calibration-alice/pause')
# Bob and Charlie's streams continue unaffected
```

### 2. Decoder Development
### 2. Decoder Development
Stream neural data with known intentions to train and validate BCI decoders:

```python
import websockets
import json
import requests

# Create dedicated session for training
response = requests.post('http://localhost:8000/api/sessions/create',
                        json={'custom_code': 'decoder-training-v1'})
session_url = response.json()['stream_url']

# Connect and filter for specific target
async with websockets.connect(f'{session_url}?target_id=0') as ws:
    async for message in ws:
        packet = json.loads(message)['data']
        spikes = packet['spikes']['spike_counts']
        target = (packet['intention']['target_x'], packet['intention']['target_y'])
        # Train decoder: spikes -> target
```

### 3. Calibration Workflows
Query trials to build calibration sets:

```python
import requests

# Get all trials reaching for target 0
response = requests.get('http://localhost:8000/api/trials/by-target/0')
trials = response.json()['trials']  # 77 trials

# Create session for calibration
session = requests.post('http://localhost:8000/api/sessions/create',
                       json={'custom_code': 'calibration-target0'}).json()

# Stream data from each calibration trial
for trial in trials[:10]:  # First 10 trials
    trial_id = trial['trial_id']
    stream_url = f"{session['stream_url']}?trial_id={trial_id}"
    # Connect to stream_url and collect calibration data
```

### 4. Ground Truth Validation
### 4. Ground Truth Validation
Validate decoder predictions against real target positions:

```python
import websockets
import json
import requests

# Create validation session
session = requests.post('http://localhost:8000/api/sessions/create',
                       json={'custom_code': 'validation-run1'}).json()

# Stream with known targets
async with websockets.connect(session['stream_url']) as ws:
    async for message in ws:
        packet = json.loads(message)['data']
        
        # Your decoder prediction
        predicted_target = my_decoder.predict(packet['spikes'])
        
        # Ground truth
        actual_target = (packet['intention']['target_x'], 
                        packet['intention']['target_y'])
        
        # Calculate error
        error = distance(predicted_target, actual_target)
```

## Next Steps

**Phase 2: Frontend Dashboard**
- Real-time visualization of spike rasters
- Cursor trajectory plotting
- Decoder performance metrics
- WebSocket client in React/TypeScript
- Session management UI (create, list, delete sessions)

**Phase 3: Decoder Integration**
- Kalman filter decoder implementation
- Online calibration endpoint
- Ground truth comparison metrics
- A/B testing framework with session isolation

**Phase 4: Multi-Dataset Support**
- Switch between different NWB files
- Dataset selection API endpoint per session
- Unified metadata format
- Recording mode for saving streams

## Contributing

This is a research/development tool. For questions or issues:
1. Check this README first (single source of truth)
2. Examine server logs for errors
3. Run `python test_client.py 10` to validate setup
4. Review code comments in `data_loader.py` and `playback_engine.py`

## License

Research use only. Dataset from [Neural Latents Benchmark](https://neurallatents.github.io/).

---

**Last Updated**: January 12, 2026  
**Status**: ✅ MVP Complete - Multi-session architecture with 40Hz streaming and intent-based calibration API

## Troubleshooting

### Common Issues

**Port already in use (Address already in use)**
```bash
# Change port in config.py or environment variable
set SERVER_PORT=8001  # Windows
export SERVER_PORT=8001  # Linux/Mac
```

**Dataset not found**
```bash
# Verify file exists
ls data/mc_maze.nwb  # Linux/Mac
dir data\mc_maze.nwb  # Windows

# Re-download if missing
dandi download https://dandiarchive.org/dandiset/000140/draft
```

**Low stream rate (<40Hz)**
- Check server logs for errors
- Verify HDF5 file on fast storage (SSD recommended)
- Ensure no other processes accessing file
- Check timing_error in `/api/stats` endpoint

**Connection refused**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Check if sessions are running
curl http://localhost:8000/api/sessions

# Check firewall (Windows)
netsh advfirewall firewall add rule name="PhantomLink" dir=in action=allow protocol=TCP localport=8000

# Try 127.0.0.1 instead of localhost
ws://127.0.0.1:8000/stream/my-session
```

**Session not found**
```bash
# List active sessions
curl http://localhost:8000/api/sessions

# Create session explicitly before connecting
curl -X POST http://localhost:8000/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"custom_code": "my-session"}'

# Or let WebSocket auto-create on connect
ws://localhost:8000/stream/my-session
```

**Too many sessions (max limit reached)**
```bash
# Delete unused sessions
curl -X DELETE http://localhost:8000/api/sessions/{session_code}

# Trigger cleanup of expired sessions
curl -X POST http://localhost:8000/api/sessions/cleanup

# Oldest sessions auto-evicted via LRU when hitting limit
```

**AttributeError: 'VectorIndex' object has no attribute 'item'**
- This is a pynwb version issue
- Ensure pynwb >= 3.1.3: `pip install --upgrade pynwb`

**Numpy/h5py incompatibility errors**
- Upgrade both: `pip install --upgrade numpy h5py`
- Requires numpy >= 2.0 for Python 3.12+

### Performance Tuning

**Check current performance:**
```bash
curl http://localhost:8000/api/stats
```

**Optimize for higher throughput:**
- Use SSD storage for NWB file
- Increase process priority (Windows Task Manager / Linux `nice`)
- Close unnecessary background applications
- Monitor CPU usage (should be <10% per core)

### Debug Mode

Enable verbose logging:
```python
# In config.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Running Tests

PhantomLink includes a comprehensive test suite covering models, data loading, streaming engine, session management, and API endpoints.

### Quick Test Run

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest -v

# Windows batch file
test.bat
```

### Test Suites

```bash
# Unit tests only
pytest test_models.py test_data_loader.py test_playback_engine.py test_session_manager.py -v

# Integration tests
pytest test_server.py -v

# With coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# Windows: specific test suite
test.bat unit          # Unit tests
test.bat integration   # Integration tests  
test.bat coverage      # With coverage
test.bat fast          # Skip slow tests
```

### Test Files

| File | Coverage | Type |
|------|----------|------|
| `test_models.py` | Pydantic models | Unit |
| `test_data_loader.py` | NWB data access | Unit |
| `test_playback_engine.py` | 40Hz streaming | Unit |
| `test_session_manager.py` | Multi-session | Unit |
| `test_server.py` | FastAPI endpoints | Integration |
| `test_calibration.py` | Manual testing | Integration |
| `test_client.py` | Stream validation | Integration |
| `test_multi_session.py` | Session isolation | Integration |

### Coverage Report

View detailed coverage:
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### CI/CD

Tests run automatically on GitHub Actions for:
- Push to `main` or `develop` branches
- Pull requests
- Multiple Python versions (3.9, 3.10, 3.11)
- Multiple OS (Ubuntu, Windows, macOS)

See `.github/workflows/tests.yml` for configuration.

### Documentation

- **Full testing guide**: [TESTING.md](TESTING.md)
- **Quick reference**: [TEST_REFERENCE.md](TEST_REFERENCE.md)
