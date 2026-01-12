"""
Integration tests for the FastAPI server (server.py).

Tests REST API endpoints and WebSocket streaming.
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from pathlib import Path


# Import after ensuring test data exists
DATA_PATH = Path(__file__).parent.parent / "data" / "raw" / "mc_maze.nwb"


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    if not DATA_PATH.exists():
        pytest.skip(f"Test data not found at {DATA_PATH}")
    
    # Import here to avoid issues if data doesn't exist
    from phantomlink.server import app
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test GET /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def test_create_session(self, client):
        """Test POST /api/sessions endpoint."""
        response = client.post("/api/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert 'session_code' in data
        assert isinstance(data['session_code'], str)
        assert len(data['session_code']) > 0
    
    def test_list_sessions(self, client):
        """Test GET /api/sessions endpoint."""
        # Create a session first
        create_response = client.post("/api/sessions")
        assert create_response.status_code == 200
        
        # List sessions
        response = client.get("/api/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert 'sessions' in data
        assert isinstance(data['sessions'], list)
        assert len(data['sessions']) > 0
    
    def test_delete_session(self, client):
        """Test DELETE /api/sessions/{session_code} endpoint."""
        # Create a session
        create_response = client.post("/api/sessions")
        session_code = create_response.json()['session_code']
        
        # Delete it
        response = client.delete(f"/api/sessions/{session_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'deleted'
    
    def test_delete_nonexistent_session(self, client):
        """Test deleting a nonexistent session."""
        response = client.delete("/api/sessions/nonexistent-session-123")
        assert response.status_code == 404


class TestMetadataEndpoint:
    """Test metadata endpoint."""
    
    def test_get_metadata(self, client):
        """Test GET /api/metadata endpoint."""
        response = client.get("/api/metadata")
        assert response.status_code == 200
        
        data = response.json()
        assert 'num_channels' in data
        assert 'duration_seconds' in data
        assert 'sampling_rate_hz' in data
        
        assert data['num_channels'] > 0
        assert data['duration_seconds'] > 0
        assert data['sampling_rate_hz'] > 0


class TestTrialEndpoints:
    """Test trial query endpoints."""
    
    def test_get_all_trials(self, client):
        """Test GET /api/trials endpoint."""
        response = client.get("/api/trials")
        assert response.status_code == 200
        
        data = response.json()
        assert 'trials' in data
        assert 'count' in data
        assert isinstance(data['trials'], list)
        assert data['count'] >= 0
    
    def test_get_trial_by_id(self, client):
        """Test GET /api/trials/{trial_id} endpoint."""
        # First get all trials to find a valid ID
        trials_response = client.get("/api/trials")
        trials = trials_response.json()['trials']
        
        if len(trials) == 0:
            pytest.skip("No trials in dataset")
        
        trial_id = trials[0]['trial_id']
        
        # Get specific trial
        response = client.get(f"/api/trials/{trial_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data['trial_id'] == trial_id
        assert 'start_time' in data
        assert 'stop_time' in data
    
    def test_get_nonexistent_trial(self, client):
        """Test getting a nonexistent trial."""
        response = client.get("/api/trials/999999")
        assert response.status_code == 404
    
    def test_get_trials_by_target(self, client):
        """Test GET /api/trials/by-target/{target_index} endpoint."""
        response = client.get("/api/trials/by-target/0")
        assert response.status_code == 200
        
        data = response.json()
        assert 'trials' in data
        assert 'count' in data
        assert isinstance(data['trials'], list)


class TestPlaybackControlEndpoints:
    """Test playback control endpoints."""
    
    def test_pause_resume(self, client):
        """Test POST /api/playback/pause and /resume endpoints."""
        # Create session
        session_response = client.post("/api/sessions")
        session_code = session_response.json()['session_code']
        
        # Pause
        response = client.post(f"/api/playback/pause?session_code={session_code}")
        assert response.status_code == 200
        
        # Resume
        response = client.post(f"/api/playback/resume?session_code={session_code}")
        assert response.status_code == 200
    
    def test_reset(self, client):
        """Test POST /api/playback/reset endpoint."""
        # Create session
        session_response = client.post("/api/sessions")
        session_code = session_response.json()['session_code']
        
        # Reset
        response = client.post(f"/api/playback/reset?session_code={session_code}")
        assert response.status_code == 200
    
    def test_seek(self, client):
        """Test POST /api/playback/seek endpoint."""
        # Create session
        session_response = client.post("/api/sessions")
        session_code = session_response.json()['session_code']
        
        # Seek to 5 seconds
        response = client.post(
            f"/api/playback/seek?session_code={session_code}",
            json={"time_s": 5.0}
        )
        assert response.status_code == 200
    
    def test_playback_control_without_session(self, client):
        """Test playback controls without valid session."""
        response = client.post("/api/playback/pause?session_code=invalid-123")
        assert response.status_code == 404


class TestWebSocket:
    """Test WebSocket streaming endpoint."""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection."""
        with client.websocket_connect("/stream") as websocket:
            # Should receive metadata first
            data = websocket.receive_json()
            assert data['type'] == 'metadata'
            assert 'num_channels' in data
    
    def test_websocket_streaming(self, client):
        """Test receiving stream packets via WebSocket."""
        with client.websocket_connect("/stream") as websocket:
            # Skip metadata
            metadata = websocket.receive_json()
            assert metadata['type'] == 'metadata'
            
            # Receive data packets
            for i in range(5):
                data = websocket.receive_json()
                assert data['type'] == 'data'
                
                packet = data['data']
                assert 'timestamp' in packet
                assert 'sequence_number' in packet
                assert 'spikes' in packet
                assert 'kinematics' in packet
                assert 'intention' in packet
    
    def test_websocket_with_session(self, client):
        """Test WebSocket with specific session code."""
        # Create session
        session_response = client.post("/api/sessions")
        session_code = session_response.json()['session_code']
        
        # Connect with session code
        with client.websocket_connect(f"/stream?session_code={session_code}") as websocket:
            metadata = websocket.receive_json()
            assert metadata['type'] == 'metadata'
    
    def test_websocket_with_target_filter(self, client):
        """Test WebSocket with target_id filter."""
        with client.websocket_connect("/stream?target_id=0") as websocket:
            # Skip metadata
            metadata = websocket.receive_json()
            
            # Check filtered packets
            for i in range(3):
                data = websocket.receive_json()
                packet = data['data']
                # Should only get packets for target 0
                assert packet['intention']['target_id'] == 0
    
    def test_websocket_with_trial_filter(self, client):
        """Test WebSocket with trial_id filter."""
        # Get a valid trial ID first
        trials_response = client.get("/api/trials")
        trials = trials_response.json()['trials']
        
        if len(trials) == 0:
            pytest.skip("No trials in dataset")
        
        trial_id = trials[0]['trial_id']
        
        with client.websocket_connect(f"/stream?trial_id={trial_id}") as websocket:
            # Skip metadata
            metadata = websocket.receive_json()
            
            # Check filtered packets
            for i in range(3):
                data = websocket.receive_json()
                packet = data['data']
                assert packet['trial_id'] == trial_id


class TestCORS:
    """Test CORS headers."""
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # CORS headers should be present
        assert 'access-control-allow-origin' in response.headers


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint."""
        response = client.get("/api/invalid")
        assert response.status_code == 404
    
    def test_invalid_trial_id_type(self, client):
        """Test invalid trial ID type."""
        response = client.get("/api/trials/invalid")
        assert response.status_code == 422  # Validation error
    
    def test_invalid_seek_time(self, client):
        """Test seek with invalid time."""
        session_response = client.post("/api/sessions")
        session_code = session_response.json()['session_code']
        
        # Negative time should fail
        response = client.post(
            f"/api/playback/seek?session_code={session_code}",
            json={"time_s": -1.0}
        )
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
