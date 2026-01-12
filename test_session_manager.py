"""
Unit tests for session manager (session_manager.py).

Tests multi-session isolation, session lifecycle, and cleanup.
"""
import pytest
import asyncio
import time
from pathlib import Path
from session_manager import SessionManager


DATA_PATH = Path(__file__).parent / "data" / "mc_maze.nwb"


@pytest.fixture
def manager():
    """Create a session manager instance for testing."""
    if not DATA_PATH.exists():
        pytest.skip(f"Test data not found at {DATA_PATH}")
    return SessionManager(DATA_PATH, max_sessions=5, session_ttl=60)


class TestSessionManager:
    """Test SessionManager class."""
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.data_path == DATA_PATH
        assert manager.max_sessions == 5
        assert manager.session_ttl == 60
        assert len(manager._sessions) == 0
    
    def test_create_session(self, manager):
        """Test creating a new session."""
        session_code = manager.create_session()
        
        assert isinstance(session_code, str)
        assert len(session_code) > 0
        assert session_code in manager._sessions
        
        session = manager._sessions[session_code]
        assert session['engine'] is not None
        assert 'created_at' in session
        assert 'last_activity' in session
    
    def test_session_code_format(self, manager):
        """Test session code format (readable codes)."""
        session_code = manager.create_session()
        
        # Should be in format "word-word-number"
        parts = session_code.split('-')
        assert len(parts) == 3
        assert parts[0].isalpha()  # adjective
        assert parts[1].isalpha()  # noun
        assert parts[2].isdigit()  # number
    
    def test_get_session(self, manager):
        """Test retrieving an existing session."""
        session_code = manager.create_session()
        
        engine = manager.get_session(session_code)
        assert engine is not None
        
        # Getting session should update last_activity
        session = manager._sessions[session_code]
        assert session['last_activity'] > session['created_at']
    
    def test_get_nonexistent_session(self, manager):
        """Test retrieving a nonexistent session."""
        engine = manager.get_session("nonexistent-session-123")
        assert engine is None
    
    def test_remove_session(self, manager):
        """Test removing a session."""
        session_code = manager.create_session()
        assert session_code in manager._sessions
        
        manager.remove_session(session_code)
        assert session_code not in manager._sessions
    
    def test_remove_nonexistent_session(self, manager):
        """Test removing a nonexistent session (should not error)."""
        manager.remove_session("nonexistent-session-123")  # Should not raise
    
    def test_list_sessions(self, manager):
        """Test listing all active sessions."""
        # Create multiple sessions
        codes = [manager.create_session() for _ in range(3)]
        
        sessions = manager.list_sessions()
        assert len(sessions) == 3
        
        for session in sessions:
            assert 'session_code' in session
            assert 'created_at' in session
            assert 'last_activity' in session
            assert session['session_code'] in codes
    
    def test_max_sessions_limit(self, manager):
        """Test that max_sessions limit is enforced (LRU eviction)."""
        # Create max_sessions
        codes = []
        for i in range(manager.max_sessions):
            code = manager.create_session()
            codes.append(code)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        assert len(manager._sessions) == manager.max_sessions
        
        # Create one more - should evict oldest
        new_code = manager.create_session()
        assert len(manager._sessions) == manager.max_sessions
        
        # First session should be evicted
        assert codes[0] not in manager._sessions
        assert new_code in manager._sessions
    
    def test_cleanup_expired_sessions(self, manager):
        """Test cleaning up expired sessions."""
        # Create session with very short TTL
        short_ttl_manager = SessionManager(DATA_PATH, max_sessions=5, session_ttl=0.1)
        
        session_code = short_ttl_manager.create_session()
        assert session_code in short_ttl_manager._sessions
        
        # Wait for session to expire
        time.sleep(0.2)
        
        # Run cleanup
        removed = short_ttl_manager.cleanup_expired_sessions()
        assert removed > 0
        assert session_code not in short_ttl_manager._sessions
    
    def test_session_isolation(self, manager):
        """Test that sessions are isolated from each other."""
        code1 = manager.create_session()
        code2 = manager.create_session()
        
        engine1 = manager.get_session(code1)
        engine2 = manager.get_session(code2)
        
        # Should be different engine instances
        assert engine1 is not engine2
        
        # Each should have independent state
        assert engine1._sequence_number == 0
        assert engine2._sequence_number == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, manager):
        """Test multiple sessions streaming concurrently."""
        code1 = manager.create_session()
        code2 = manager.create_session()
        
        engine1 = manager.get_session(code1)
        engine2 = manager.get_session(code2)
        
        await engine1.start()
        await engine2.start()
        
        # Get packets from both engines
        packet1 = None
        packet2 = None
        
        async for p in engine1.stream():
            packet1 = p
            break
        
        async for p in engine2.stream():
            packet2 = p
            break
        
        # Both should have received packets
        assert packet1 is not None
        assert packet2 is not None
        
        # Sequences should be independent
        # (might be same if both just started, but structures are different)
        assert packet1 is not packet2
        
        await engine1.stop()
        await engine2.stop()
    
    def test_session_metadata(self, manager):
        """Test session metadata tracking."""
        session_code = manager.create_session()
        
        sessions = manager.list_sessions()
        session = sessions[0]
        
        assert session['session_code'] == session_code
        assert isinstance(session['created_at'], float)
        assert isinstance(session['last_activity'], float)
        assert session['last_activity'] >= session['created_at']
    
    def test_unique_session_codes(self, manager):
        """Test that session codes are unique."""
        codes = set()
        for _ in range(20):
            code = manager.create_session()
            assert code not in codes
            codes.add(code)
    
    def test_session_activity_updates(self, manager):
        """Test that accessing session updates last_activity."""
        session_code = manager.create_session()
        
        session = manager._sessions[session_code]
        initial_activity = session['last_activity']
        
        time.sleep(0.1)
        
        # Access session
        manager.get_session(session_code)
        
        updated_activity = session['last_activity']
        assert updated_activity > initial_activity


class TestSessionLifecycle:
    """Test complete session lifecycle scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, manager):
        """Test complete session from creation to cleanup."""
        # Create session
        session_code = manager.create_session()
        assert session_code in manager._sessions
        
        # Get engine
        engine = manager.get_session(session_code)
        assert engine is not None
        
        # Start streaming
        await engine.start()
        assert engine.is_running
        
        # Stream some data
        packet_count = 0
        async for packet in engine.stream():
            packet_count += 1
            if packet_count >= 5:
                break
        
        assert packet_count == 5
        
        # Stop streaming
        await engine.stop()
        assert not engine.is_running
        
        # Remove session
        manager.remove_session(session_code)
        assert session_code not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_session_reuse(self, manager):
        """Test that a session can be reused multiple times."""
        session_code = manager.create_session()
        engine = manager.get_session(session_code)
        
        # First use
        await engine.start()
        async for _ in engine.stream():
            break
        await engine.stop()
        
        # Reset and reuse
        engine.reset()
        await engine.start()
        async for _ in engine.stream():
            break
        await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
