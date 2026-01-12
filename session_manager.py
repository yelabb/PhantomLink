"""
Session management for multi-client isolation.

Each session gets its own PlaybackEngine instance with independent state,
while sharing the underlying DataLoader (read-only, memory-mapped).
"""
import logging
import time
import secrets
from typing import Dict, Optional, List
from pathlib import Path
from collections import OrderedDict

from playback_engine import PlaybackEngine
from data_loader import MC_MazeLoader

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages multiple isolated playback sessions.
    
    Each session has:
    - Unique session code (e.g., 'swift-neural-42')
    - Independent PlaybackEngine instance
    - Own playback state (position, pause, filters)
    - Last activity timestamp for cleanup
    
    Sessions share a single DataLoader (memory-mapped, thread-safe reads).
    """
    
    # Adjectives and nouns for readable session codes
    ADJECTIVES = ['swift', 'bright', 'clever', 'neural', 'quantum', 'cosmic', 
                  'rapid', 'dynamic', 'active', 'smart', 'fast', 'prime']
    NOUNS = ['brain', 'cortex', 'synapse', 'neuron', 'signal', 'wave',
             'pulse', 'mind', 'link', 'node', 'core', 'stream']
    
    def __init__(self, data_path: Path, max_sessions: int = 100, session_ttl: int = 3600):
        """
        Initialize session manager.
        
        Args:
            data_path: Path to NWB dataset file
            max_sessions: Maximum concurrent sessions (LRU eviction)
            session_ttl: Session timeout in seconds (default: 1 hour)
        """
        self.data_path = data_path
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        
        # Shared data loader (read-only, memory-mapped)
        self.shared_loader: Optional[MC_MazeLoader] = None
        
        # Session storage: {session_code: {'engine': PlaybackEngine, 'created': timestamp, 'last_active': timestamp}}
        self.sessions: OrderedDict[str, Dict] = OrderedDict()
        
        # Initialize shared loader
        self._initialize_shared_loader()
    
    def _initialize_shared_loader(self):
        """Initialize the shared data loader once."""
        logger.info(f"Initializing shared data loader: {self.data_path}")
        self.shared_loader = MC_MazeLoader(self.data_path, lazy_load=True)
        logger.info(f"Shared loader ready: {self.shared_loader.num_channels} channels, "
                   f"{self.shared_loader.duration:.1f}s, {len(self.shared_loader.get_trials())} trials")
    
    def _generate_session_code(self) -> str:
        """Generate a readable session code (e.g., 'swift-neural-42')."""
        adjective = secrets.choice(self.ADJECTIVES)
        noun = secrets.choice(self.NOUNS)
        number = secrets.randbelow(100)
        return f"{adjective}-{noun}-{number}"
    
    def create_session(self, session_code: Optional[str] = None) -> str:
        """
        Create a new session with isolated playback state.
        
        Args:
            session_code: Optional custom session code. If None, generates random code.
        
        Returns:
            Session code for the new session
        """
        # Generate code if not provided
        if session_code is None:
            session_code = self._generate_session_code()
            # Ensure uniqueness
            while session_code in self.sessions:
                session_code = self._generate_session_code()
        
        # Check if session already exists
        if session_code in self.sessions:
            logger.warning(f"Session {session_code} already exists, returning existing session")
            self._update_activity(session_code)
            return session_code
        
        # Enforce max sessions (LRU eviction)
        if len(self.sessions) >= self.max_sessions:
            self._evict_oldest_session()
        
        # Create new PlaybackEngine for this session
        # Note: PlaybackEngine will use the shared loader internally
        engine = PlaybackEngine(self.data_path)
        engine.loader = self.shared_loader  # Share the loader instance
        
        # Store session
        now = time.time()
        self.sessions[session_code] = {
            'engine': engine,
            'created': now,
            'last_active': now,
            'connections': 0
        }
        
        logger.info(f"Created session: {session_code} (total sessions: {len(self.sessions)})")
        return session_code
    
    def get_session(self, session_code: str) -> Optional[PlaybackEngine]:
        """
        Get playback engine for a session.
        
        Args:
            session_code: Session identifier
        
        Returns:
            PlaybackEngine instance or None if session not found
        """
        if session_code not in self.sessions:
            return None
        
        self._update_activity(session_code)
        return self.sessions[session_code]['engine']
    
    def _update_activity(self, session_code: str):
        """Update last activity timestamp for a session."""
        if session_code in self.sessions:
            self.sessions[session_code]['last_active'] = time.time()
            # Move to end (most recently used)
            self.sessions.move_to_end(session_code)
    
    def increment_connections(self, session_code: str):
        """Increment active connection count for a session."""
        if session_code in self.sessions:
            self.sessions[session_code]['connections'] += 1
    
    def decrement_connections(self, session_code: str):
        """Decrement active connection count for a session."""
        if session_code in self.sessions:
            self.sessions[session_code]['connections'] = max(0, 
                self.sessions[session_code]['connections'] - 1)
    
    def delete_session(self, session_code: str) -> bool:
        """
        Delete a session and cleanup resources.
        
        Args:
            session_code: Session to delete
        
        Returns:
            True if deleted, False if not found
        """
        if session_code not in self.sessions:
            return False
        
        session = self.sessions[session_code]
        
        # Check for active connections
        if session['connections'] > 0:
            logger.warning(f"Cannot delete session {session_code}: {session['connections']} active connections")
            return False
        
        # Stop playback engine
        session['engine'].stop()
        
        # Remove session
        del self.sessions[session_code]
        logger.info(f"Deleted session: {session_code} (remaining: {len(self.sessions)})")
        return True
    
    def _evict_oldest_session(self):
        """Evict the least recently used session."""
        if not self.sessions:
            return
        
        # OrderedDict maintains insertion order, oldest first
        oldest_code = next(iter(self.sessions))
        oldest = self.sessions[oldest_code]
        
        # Skip if has active connections
        if oldest['connections'] > 0:
            logger.warning(f"Cannot evict session {oldest_code}: has active connections")
            return
        
        logger.info(f"Evicting oldest session: {oldest_code}")
        self.delete_session(oldest_code)
    
    def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded TTL with no active connections."""
        now = time.time()
        expired = []
        
        for code, session in self.sessions.items():
            age = now - session['last_active']
            if age > self.session_ttl and session['connections'] == 0:
                expired.append(code)
        
        for code in expired:
            logger.info(f"Cleaning up expired session: {code} (inactive for {self.session_ttl}s)")
            self.delete_session(code)
        
        return len(expired)
    
    def list_sessions(self) -> List[Dict]:
        """
        Get list of all active sessions with metadata.
        
        Returns:
            List of session info dictionaries
        """
        now = time.time()
        return [
            {
                'session_code': code,
                'created': session['created'],
                'last_active': session['last_active'],
                'age_seconds': now - session['created'],
                'idle_seconds': now - session['last_active'],
                'connections': session['connections'],
                'is_running': session['engine'].is_running,
                'is_paused': session['engine'].is_paused,
                'current_index': session['engine']._current_index,
                'packets_sent': session['engine']._packets_sent
            }
            for code, session in self.sessions.items()
        ]
    
    def get_stats(self) -> Dict:
        """Get overall session manager statistics."""
        return {
            'total_sessions': len(self.sessions),
            'max_sessions': self.max_sessions,
            'session_ttl': self.session_ttl,
            'active_connections': sum(s['connections'] for s in self.sessions.values()),
            'running_sessions': sum(1 for s in self.sessions.values() if s['engine'].is_running),
            'shared_loader_channels': self.shared_loader.num_channels if self.shared_loader else 0,
            'shared_loader_trials': len(self.shared_loader.get_trials()) if self.shared_loader else 0
        }
    
    async def cleanup(self):
        """Cleanup all sessions and shared resources."""
        logger.info("Cleaning up session manager...")
        
        # Stop all sessions
        for code in list(self.sessions.keys()):
            self.delete_session(code)
        
        # Close shared loader
        if self.shared_loader:
            self.shared_loader.close()
        
        logger.info("Session manager cleanup complete")
