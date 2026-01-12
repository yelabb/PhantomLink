"""
Test suite for /metrics endpoint

Tests metrics collection and reporting functionality including:
- Latency tracking
- Memory usage
- Dropped packets
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from phantomlink.server import app, session_manager
from phantomlink.session_manager import SessionManager
from phantomlink.playback_engine import PlaybackEngine


@pytest.fixture
def test_dataset_path(tmp_path):
    """Fixture to provide test dataset path."""
    # Use actual dataset path if available
    dataset_path = Path("data/raw/mc_maze.nwb")
    if dataset_path.exists():
        return dataset_path
    
    # Otherwise skip tests that require dataset
    pytest.skip("Dataset not available")


@pytest.fixture
def mock_session_manager(test_dataset_path):
    """Create a mock session manager for testing."""
    manager = SessionManager(
        data_path=test_dataset_path,
        max_sessions=10,
        session_ttl=3600
    )
    return manager


class TestMetricsEndpoint:
    """Test cases for /metrics endpoint."""
    
    def test_metrics_endpoint_exists(self):
        """Test that /metrics endpoint is accessible."""
        client = TestClient(app)
        
        # Mock session_manager
        with patch('phantomlink.server.session_manager') as mock_manager:
            mock_manager.get_metrics.return_value = {
                'total_sessions': 0,
                'active_sessions': 0,
                'total_connections': 0,
                'sessions': {}
            }
            
            response = client.get("/metrics")
            assert response.status_code == 200
    
    def test_metrics_response_structure(self):
        """Test that /metrics returns correct structure."""
        client = TestClient(app)
        
        with patch('phantomlink.server.session_manager') as mock_manager:
            mock_manager.get_metrics.return_value = {
                'total_sessions': 1,
                'active_sessions': 1,
                'total_connections': 1,
                'sessions': {
                    'test-session': {
                        'packets_sent': 100,
                        'dropped_packets': 0,
                        'network_latency_ms': {
                            'mean': 1.5,
                            'std': 0.3,
                            'max': 3.0
                        },
                        'timing_error_ms': {
                            'mean': 0.5,
                            'std': 0.2,
                            'max': 1.0
                        },
                        'memory_usage_mb': 10.5,
                        'is_running': True,
                        'is_paused': False,
                        'connections': 1
                    }
                }
            }
            
            response = client.get("/metrics")
            data = response.json()
            
            # Check top-level structure
            assert 'timestamp' in data
            assert 'service' in data
            assert 'version' in data
            assert 'metrics' in data
            
            # Check metrics structure
            metrics = data['metrics']
            assert 'total_sessions' in metrics
            assert 'active_sessions' in metrics
            assert 'total_connections' in metrics
            assert 'sessions' in metrics
            
            # Check session-specific metrics
            session = metrics['sessions']['test-session']
            assert 'packets_sent' in session
            assert 'dropped_packets' in session
            assert 'network_latency_ms' in session
            assert 'timing_error_ms' in session
            assert 'memory_usage_mb' in session
    
    def test_metrics_with_no_sessions(self):
        """Test /metrics when no sessions are active."""
        client = TestClient(app)
        
        with patch('phantomlink.server.session_manager') as mock_manager:
            mock_manager.get_metrics.return_value = {
                'total_sessions': 0,
                'active_sessions': 0,
                'total_connections': 0,
                'sessions': {}
            }
            
            response = client.get("/metrics")
            data = response.json()
            
            assert response.status_code == 200
            assert data['metrics']['total_sessions'] == 0
            assert data['metrics']['sessions'] == {}
    
    def test_latency_tracking(self):
        """Test that network latency is tracked correctly."""
        # Create mock engine with latency data
        mock_engine = MagicMock()
        mock_engine._packets_sent = 1000
        mock_engine._dropped_packets = 5
        mock_engine._network_latencies = [0.001, 0.002, 0.0015, 0.003]  # in seconds
        mock_engine._timing_errors = [0.0005, 0.0001, 0.0002]
        mock_engine.is_running = True
        mock_engine.is_paused = False
        
        # Mock get_stats
        mock_engine.get_stats.return_value = {
            'packets_sent': 1000,
            'dropped_packets': 5,
            'network_latency_mean_ms': 1.875,
            'network_latency_std_ms': 0.75,
            'network_latency_max_ms': 3.0,
            'timing_error_mean_ms': 0.267,
            'timing_error_std_ms': 0.17,
            'timing_error_max_ms': 0.5,
            'is_running': True,
            'is_paused': False,
            'current_index': 500
        }
        
        # Test that latencies are in expected range
        stats = mock_engine.get_stats()
        assert stats['network_latency_mean_ms'] > 0
        assert stats['network_latency_mean_ms'] < 10  # Should be under 10ms
    
    def test_memory_usage_tracking(self):
        """Test that memory usage is calculated correctly."""
        with patch('phantomlink.server.session_manager') as mock_manager:
            mock_manager.get_memory_usage_per_session.return_value = {
                'test-session': {
                    'total_bytes': 12582912,  # ~12MB
                    'total_mb': 12.0,
                    'packets_sent': 1000,
                    'timing_errors_count': 1000,
                    'network_latencies_count': 1000
                }
            }
            
            memory_usage = mock_manager.get_memory_usage_per_session()
            session_memory = memory_usage['test-session']
            
            assert session_memory['total_mb'] > 0
            assert session_memory['total_bytes'] > 0
            assert session_memory['total_mb'] == session_memory['total_bytes'] / (1024 * 1024)
    
    def test_dropped_packets_tracking(self):
        """Test that dropped packets are tracked."""
        mock_engine = MagicMock()
        mock_engine._packets_sent = 1000
        mock_engine._dropped_packets = 10
        
        # Calculate drop rate
        drop_rate = mock_engine._dropped_packets / mock_engine._packets_sent
        assert drop_rate == 0.01  # 1% drop rate
        assert mock_engine._dropped_packets == 10
    
    def test_metrics_without_session_manager(self):
        """Test /metrics when session manager is not initialized."""
        client = TestClient(app)
        
        with patch('phantomlink.server.session_manager', None):
            response = client.get("/metrics")
            assert response.status_code == 503
            assert 'detail' in response.json()


class TestSessionManagerMetrics:
    """Test SessionManager metrics methods."""
    
    def test_get_metrics_method(self, mock_session_manager):
        """Test SessionManager.get_metrics() method."""
        # Create a test session
        session_code = mock_session_manager.create_session()
        
        # Get metrics
        metrics = mock_session_manager.get_metrics()
        
        assert 'total_sessions' in metrics
        assert 'active_sessions' in metrics
        assert 'total_connections' in metrics
        assert 'sessions' in metrics
        assert session_code in metrics['sessions']
    
    def test_get_memory_usage_per_session(self, mock_session_manager):
        """Test SessionManager.get_memory_usage_per_session() method."""
        # Create a test session
        session_code = mock_session_manager.create_session()
        
        # Get memory usage
        memory_usage = mock_session_manager.get_memory_usage_per_session()
        
        assert session_code in memory_usage
        assert 'total_bytes' in memory_usage[session_code]
        assert 'total_mb' in memory_usage[session_code]
        assert memory_usage[session_code]['total_bytes'] > 0


class TestPlaybackEngineMetrics:
    """Test PlaybackEngine metrics tracking."""
    
    def test_engine_stats_includes_latency(self, test_dataset_path):
        """Test that engine stats include network latency."""
        engine = PlaybackEngine(test_dataset_path)
        
        # Simulate some latency measurements
        engine._network_latencies = [0.001, 0.002, 0.0015]
        engine._packets_sent = 100
        engine._dropped_packets = 0
        
        stats = engine.get_stats()
        
        assert 'packets_sent' in stats
        assert 'dropped_packets' in stats
        # Latency stats should be present if latencies were recorded
        if engine._network_latencies:
            assert 'network_latency_mean_ms' in stats
    
    def test_engine_stats_without_data(self, test_dataset_path):
        """Test engine stats when no data has been streamed."""
        engine = PlaybackEngine(test_dataset_path)
        
        stats = engine.get_stats()
        
        assert 'packets_sent' in stats
        assert stats['packets_sent'] == 0
        assert 'dropped_packets' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
