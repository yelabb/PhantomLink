# Changelog

All notable changes to PhantomLink will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Metrics endpoint** (`/metrics`) for system monitoring
  - Real-time latency tracking (tick-to-network)
  - Memory usage per session
  - Dropped packets counter
  - Timing error statistics
- Comprehensive metrics guide ([METRICS_GUIDE.md](docs/METRICS_GUIDE.md))
- Metrics monitoring example script ([examples/metrics_monitor.py](examples/metrics_monitor.py))
- Unit tests for metrics functionality ([tests/test_metrics.py](tests/test_metrics.py))

### Changed
- Enhanced `PlaybackEngine.get_stats()` to include network latency and dropped packets
- Extended `SessionManager` with `get_metrics()` and `get_memory_usage_per_session()` methods
- Updated README with metrics endpoint documentation

### Technical Details
- Network latency measured from packet generation to WebSocket send
- Memory usage calculated using `sys.getsizeof()` for session objects
- Metrics stored in rolling buffers (last 1000 samples) to prevent memory growth
- Latency tracking implemented in WebSocket handler for accurate tick-to-network measurement

## [0.2.0] - 2026-01-12

### Added
- Multi-session isolation with independent playback states
- Session management API (create, list, delete, cleanup)
- Shareable session URLs with readable session codes
- Noise injection middleware for robustness testing
- MessagePack serialization protocol (60% size reduction vs JSON)
- LSL streaming support
- Playback control (pause/resume/seek) per session
- Intent-based filtering (by target_id or trial_id)
- Trial metadata API
- Memory-mapped NWB/HDF5 lazy loading
- Comprehensive documentation and examples

### Changed
- Migrated from single-session to multi-session architecture
- Improved timing accuracy with soft real-time guarantees (1-15ms jitter)
- Enhanced API structure with RESTful endpoints

### Fixed
- Memory leaks in long-running sessions
- Timing drift issues in extended streaming
- Session cleanup and TTL management

## [0.1.0] - 2025-12-01

### Added
- Initial release
- Basic 40Hz neural data streaming
- WebSocket protocol support
- MC_Maze dataset integration
- Simple playback engine
- REST API for basic operations

[Unreleased]: https://github.com/yelabb/PhantomLink/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yelabb/PhantomLink/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yelabb/PhantomLink/releases/tag/v0.1.0
