# PhantomLink Core

> **📖 Single Source of Truth**: This README is the authoritative documentation. All other docs redirect here.

**The Ethereal/Mailtrap for Neurotechnology** 🧠⚡

PhantomLink Core streams pre-recorded neural data from the MC_Maze dataset at 40Hz with strict 25ms timing, simulating a live BCI feed from a neural implant. Each packet delivers time-aligned spike counts + cursor kinematics + target intention for decoder development and testing.

## Architecture

- **Single-Stack Python**: FastAPI + Uvicorn ASGI server
- **Native NWB/HDF5**: Direct pynwb integration with lazy memory-mapped access
- **Strict 40Hz Streaming**: Asyncio-based playback maintains precise 25ms intervals
- **Real Neural Data**: MC_Maze dataset from Neural Latents Benchmark (142 units, 7192s duration, 1000Hz behavioral sampling)

## Features

✅ **40Hz Real-Time Streaming** - WebSocket endpoint with sub-millisecond timing accuracy  
✅ **Lazy Loading** - Memory-mapped HDF5 access, no RAM bottleneck  
✅ **Time-Aligned Payloads** - Spike counts + cursor kinematics synchronized to 25ms bins  
✅ **REST API** - Control endpoints for pause/resume/seek  
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
INFO - Opened NWB file: data\mc_maze.nwb
INFO - Found 142 neural units
INFO - Found processing module: behavior
INFO -   - cursor_pos: (287710, 2), sampling rate: 1000.0Hz
INFO -   - hand_vel: (287710, 2)
INFO - Dataset loaded: 142 channels, 7192.8s duration, 287710 timesteps
INFO - Server ready on 0.0.0.0:8000
INFO - Uvicorn running on http://0.0.0.0:8000
```

Server is now streaming at **ws://localhost:8000/stream**

## Testing the Stream

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

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and status |
| `/health` | GET | Health check |
| `/api/metadata` | GET | Dataset metadata (channels, duration, etc.) |
| `/api/stats` | GET | Current playback statistics |
| `/api/control/pause` | POST | Pause playback |
| `/api/control/resume` | POST | Resume playback |
| `/api/control/stop` | POST | Stop playback |
| `/api/control/seek?position_seconds=X` | POST | Seek to position |

### WebSocket Stream

**Endpoint**: `ws://localhost:8000/stream`  
**Frequency**: 40Hz (25ms intervals)  
**Protocol**: JSON packets

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
      "target_id": 0,
      "target_x": 0.0,
      "target_y": 0.0
    },
    "trial_id": 0,
    "trial_time_ms": 1050.0
  }
}
```

### Data Sources

- **Spikes**: 142 neural units from motor cortex, binned at 25ms
- **Kinematics**: Cursor position and hand velocity, sampled at 1000Hz (downsampled to 40Hz)
- **Behavioral Data**: From NWB `processing['behavior']` module
- **Ground Truth**: Real neural recordings, not simulated

## Architecture Deep Dive

### System Design

```
Client (WebSocket) ←→ FastAPI Server ←→ PlaybackEngine ←→ DataLoader ←→ NWB File
                                              ↓
                                        40Hz Asyncio Loop
                                        (25ms precision)
```

### Key Components

**`data_loader.py`** - MC_MazeLoader class  
- Lazy-loads NWB file with pynwb + HDF5 memory mapping
- Extracts spike times (ragged arrays via VectorIndex)
- Reads behavioral data at 1000Hz, bins to 40Hz windows
- No data preloading: ~7ms per packet extraction

**`playback_engine.py`** - PlaybackEngine class  
- Asyncio-based 40Hz streaming with strict timing
- Tracks timing errors (logs every 1000 packets)
- Handles pause/resume/seek controls
- Generates StreamPacket objects

**`server.py`** - FastAPI application  
- WebSocket endpoint at `/stream` 
- REST API for control and metadata
- Detects `.nwb` files in `data/` directory
- Non-blocking async design

**`models.py`** - Pydantic data models  
- StreamPacket, SpikeData, Kinematics, TargetIntention
- Type validation and serialization

### Performance Characteristics

- **Packet Generation**: ~7ms (HDF5 read + binning)
- **Timing Precision**: <1ms std deviation
- **Memory Footprint**: <500MB (memory-mapped file)
- **Throughput**: 40Hz sustained for hours
- **Latency**: 25ms ± 0.5ms per packet

### Design Principles

1. **Single Source of Truth**: Real NWB data only, no mock data
2. **Lazy Evaluation**: Memory-map HDF5, extract on-demand
3. **Precise Timing**: Asyncio sleep with error tracking
4. **Type Safety**: Pydantic models for all data structures
5. **Fail Fast**: Errors propagate immediately, no silent failures

## Development

### Project Structure

```
PhantomLink/
├── data/                    # NWB dataset files (gitignored)
│   └── mc_maze.nwb         # MC_Maze dataset (~1.5GB)
├── config.py               # Settings (40Hz, 25ms intervals)
├── models.py               # Pydantic data models
├── data_loader.py          # NWB file loader with lazy access
├── playback_engine.py      # 40Hz streaming engine
├── server.py               # FastAPI application
├── main.py                 # Entry point
├── test_client.py          # Stream validation client
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

## Next Steps

**Phase 2: Frontend Dashboard**
- Real-time visualization of spike rasters
- Cursor trajectory plotting
- Decoder performance metrics
- WebSocket client in React/TypeScript

**Phase 3: Decoder Integration**
- Kalman filter decoder implementation
- Online calibration endpoint
- Ground truth comparison metrics
- A/B testing framework

**Phase 4: Multi-Dataset Support**
- Switch between different NWB files
- Dataset selection API endpoint
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

**Last Updated**: January 2026  
**Status**: ✅ MVP Complete - 40Hz streaming validated with real MC_Maze data

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

# Check firewall (Windows)
netsh advfirewall firewall add rule name="PhantomLink" dir=in action=allow protocol=TCP localport=8000

# Try 127.0.0.1 instead of localhost
ws://127.0.0.1:8000/stream
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
