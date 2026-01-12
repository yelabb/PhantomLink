"""
FastAPI server with WebSocket streaming endpoint.

This module implements the REST and WebSocket API for PhantomLink Core.
"""
import logging
from pathlib import Path
from typing import Set, Optional
import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from phantomlink.config import settings
from phantomlink.models import StreamMetadata
from phantomlink.playback_engine import PlaybackEngine
from phantomlink.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PhantomLink Core",
    description="BCI Mock Server - Multi-Session Neural Data Streaming",
    version="0.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session manager
session_manager: SessionManager = None
active_connections: Set[WebSocket] = set()
cleanup_task = None


async def periodic_cleanup():
    """Background task to cleanup expired sessions every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        if session_manager:
            count = session_manager.cleanup_expired_sessions()
            if count > 0:
                logger.info(f"Periodic cleanup removed {count} expired sessions")


@app.on_event("startup")
async def startup_event():
    """Initialize the session manager on startup."""
    global session_manager, cleanup_task
    
    logger.info("Starting PhantomLink Core server")
    
    # Determine dataset path - try .nwb first, then .h5
    data_dir = Path(settings.data_dir)
    dataset_path_nwb = data_dir / f"{settings.dataset_name}.nwb"
    dataset_path_h5 = data_dir / f"{settings.dataset_name}.h5"
    
    if dataset_path_nwb.exists():
        dataset_path = dataset_path_nwb
        logger.info(f"Using NWB dataset: {dataset_path}")
    else:
        dataset_path = dataset_path_h5
        logger.info(f"Using H5 dataset: {dataset_path}")
    
    # Initialize session manager
    session_manager = SessionManager(
        dataset_path,
        max_sessions=settings.max_connections,
        session_ttl=3600  # 1 hour TTL
    )
    
    logger.info(f"Server ready on {settings.host}:{settings.port}")
    logger.info(f"Session-based isolation enabled (max {settings.max_connections} sessions)")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global session_manager, cleanup_task
    
    logger.info("Shutting down PhantomLink Core server")
    
    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
    
    # Cleanup session manager
    if session_manager:
        await session_manager.cleanup()
    
    # Close all WebSocket connections
    for connection in active_connections:
        await connection.close()
    
    logger.info("Server shutdown complete")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "PhantomLink Core",
        "version": "0.2.0",
        "description": "Multi-Session BCI Mock Server for Neurotechnology Development",
        "features": [
            "40Hz neural data streaming",
            "Session-based isolation",
            "Intent-based filtering",
            "Shareable session URLs"
        ],
        "endpoints": {
            "create_session": "POST /api/sessions/create",
            "list_sessions": "GET /api/sessions",
            "session_stats": "GET /api/sessions/{session_code}",
            "metadata": "/api/metadata",
            "trials": "/api/trials",
            "stream": "ws://localhost:8000/stream/{session_code}"
        },
        "examples": [
            "Create session: POST /api/sessions/create",
            "Stream: ws://localhost:8000/stream/swift-neural-42",
            "With filter: ws://localhost:8000/stream/swift-neural-42?target_id=0"
        ]
    }


@app.post("/api/sessions/create")
async def create_session(custom_code: Optional[str] = None):
    """Create a new isolated playback session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    session_code = session_manager.create_session(custom_code)
    
    return {
        "session_code": session_code,
        "stream_url": f"ws://localhost:{settings.port}/stream/{session_code}",
        "created": time.time(),
        "message": "Session created. Use this code to stream independent neural data."
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    sessions = session_manager.list_sessions()
    stats = session_manager.get_stats()
    
    return {
        "sessions": sessions,
        "stats": stats
    }


@app.get("/api/sessions/{session_code}")
async def get_session_stats(session_code: str):
    """Get statistics for a specific session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    engine = session_manager.get_session(session_code)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    session_info = next((s for s in session_manager.list_sessions() 
                        if s['session_code'] == session_code), None)
    
    if not session_info:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    return session_info


@app.delete("/api/sessions/{session_code}")
async def delete_session(session_code: str):
    """Delete a session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    success = session_manager.delete_session(session_code)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found or has active connections")
    
    return {"message": f"Session {session_code} deleted"}


@app.post("/api/sessions/cleanup")
async def cleanup_sessions():
    """Cleanup expired sessions."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    count = session_manager.cleanup_expired_sessions()
    return {"cleaned_up": count, "message": f"Removed {count} expired sessions"}


@app.get("/api/metadata")
async def get_metadata():
    """Get metadata about the current dataset and stream configuration."""
    if not session_manager or not session_manager.shared_loader:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    loader = session_manager.shared_loader
    return {
        "dataset": "MC_Maze",
        "num_channels": loader.num_channels,
        "duration_seconds": loader.duration,
        "total_packets": loader.num_timesteps,
        "frequency_hz": settings.stream_frequency_hz,
        "num_trials": len(loader.get_trials())
    }


@app.get("/api/trials")
async def get_trials():
    """Get list of all trials with intention/target information."""
    if not session_manager or not session_manager.shared_loader:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    trials = session_manager.shared_loader.get_trials()
    return {"trials": trials, "count": len(trials)}


@app.get("/api/trials/{trial_id}")
async def get_trial(trial_id: int):
    """Get specific trial information."""
    if not session_manager or not session_manager.shared_loader:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    trials = session_manager.shared_loader.get_trials()
    if trial_id < 0 or trial_id >= len(trials):
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")
    
    return trials[trial_id]


@app.get("/api/trials/by-target/{target_index}")
async def get_trials_by_target(target_index: int):
    """Get all trials reaching for a specific target index."""
    if not session_manager or not session_manager.shared_loader:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    trials = session_manager.shared_loader.get_trials_by_target(target_index)
    return {"trials": trials, "count": len(trials), "target_index": target_index}


@app.get("/api/stats")
async def get_stats():
    """Get current session manager statistics."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    stats = session_manager.get_stats()
    return {
        "active_connections": len(active_connections),
        "session_manager": stats
    }


@app.post("/api/control/{session_code}/pause")
async def pause_playback(session_code: str):
    """Pause playback for a specific session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    engine = session_manager.get_session(session_code)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    engine.pause()
    return {"status": "paused", "session_code": session_code}


@app.post("/api/control/{session_code}/resume")
async def resume_playback(session_code: str):
    """Resume playback for a specific session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    engine = session_manager.get_session(session_code)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    engine.resume()
    return {"status": "resumed", "session_code": session_code}


@app.post("/api/control/{session_code}/stop")
async def stop_playback(session_code: str):
    """Stop playback for a specific session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    engine = session_manager.get_session(session_code)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    engine.stop()
    return {"status": "stopped", "session_code": session_code}


@app.post("/api/control/{session_code}/seek")
async def seek_playback(session_code: str, position_seconds: float):
    """Seek to a specific position in the dataset for a specific session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    engine = session_manager.get_session(session_code)
    if not engine:
        raise HTTPException(status_code=404, detail=f"Session {session_code} not found")
    
    engine.seek(position_seconds)
    return {"status": "seeked", "position_seconds": position_seconds, "session_code": session_code}


@app.websocket("/stream/{session_code}")
async def websocket_stream(websocket: WebSocket, session_code: str, 
                          trial_id: Optional[int] = None, target_id: Optional[int] = None):
    """
    WebSocket endpoint for 40Hz neural data streaming with session isolation.
    
    Path parameters:
        session_code: Session identifier (e.g., 'swift-neural-42')
    
    Query parameters:
        trial_id: Filter to only stream packets from this trial
        target_id: Filter to only stream packets reaching for this target index
    
    Clients connect to ws://localhost:8000/stream/{session_code} to receive real-time
    packets containing time-aligned spike counts and behavioral ground truth.
    
    Each session has independent playback state (position, pause, filters).
    """
    if not session_manager:
        await websocket.close(code=1011, reason="Session manager not initialized")
        return
    
    # Get or create session
    playback_engine = session_manager.get_session(session_code)
    if not playback_engine:
        # Auto-create session if it doesn't exist
        logger.info(f"Auto-creating session: {session_code}")
        session_manager.create_session(session_code)
        playback_engine = session_manager.get_session(session_code)
    
    await websocket.accept()
    active_connections.add(websocket)
    session_manager.increment_connections(session_code)
    
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected to session {session_code}. Active connections: {len(active_connections)}")
    
    try:
        # Send initial metadata
        metadata = playback_engine.get_metadata()
        await websocket.send_json({
            "type": "metadata",
            "data": metadata.model_dump(),
            "session": {
                "code": session_code,
                "url": f"ws://localhost:{settings.port}/stream/{session_code}"
            }
        })
        
        # Start streaming packets with optional filters
        async for packet in playback_engine.stream(loop=True, trial_filter=trial_id, target_filter=target_id):
            try:
                # Send packet as JSON
                await websocket.send_json({
                    "type": "data",
                    "data": packet.model_dump()
                })
                
                # Check if client sent any control messages
                # (non-blocking receive with timeout)
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.001
                    )
                    # Handle control messages if needed
                    logger.debug(f"Received message from client: {message}")
                except asyncio.TimeoutError:
                    pass  # No message received, continue streaming
                
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected during streaming")
                break
            except Exception as e:
                logger.error(f"Error sending packet to client {client_id}: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from session {session_code}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection {client_id} (session {session_code}): {e}")
    finally:
        active_connections.discard(websocket)
        session_manager.decrement_connections(session_code)
        logger.info(f"Client {client_id} removed from session {session_code}. Active connections: {len(active_connections)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "session_manager_initialized": session_manager is not None,
        "active_connections": len(active_connections),
        "active_sessions": len(session_manager.sessions) if session_manager else 0
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False  # Set to True for development
    )
