"""
FastAPI server with WebSocket streaming endpoint.

This module implements the REST and WebSocket API for PhantomLink Core.
"""
import logging
from pathlib import Path
from typing import Set, Optional, Literal
import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from phantomlink.config import settings
from phantomlink.models import StreamMetadata
from phantomlink.playback_engine import PlaybackEngine
from phantomlink.session_manager import SessionManager
from phantomlink.lsl_streamer import LSLStreamManager
from phantomlink.serialization import serialize_for_websocket

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
lsl_manager: LSLStreamManager = None
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
    global session_manager, cleanup_task, lsl_manager
    
    logger.info("Starting PhantomLink Core server")
    
    # Initialize LSL stream manager
    lsl_manager = LSLStreamManager()
    logger.info("LSL Stream Manager initialized")
    
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
    global session_manager, cleanup_task, lsl_manager
    
    logger.info("Shutting down PhantomLink Core server")
    
    # Cancel cleanup task
    if cleanup_task:
        cleanup_task.cancel()
    
    # Cleanup LSL manager
    if lsl_manager:
        lsl_manager.cleanup_all()
    
    # Cleanup session manager
    if session_manager:
        await session_manager.cleanup()
    
    # Close all WebSocket connections
    for connection in active_connections:
        await connection.close()
    
    logger.info("Server shutdown complete")


@app.get("/")
async def root(request: Request):
    """Root endpoint with API information."""
    # Determine WebSocket scheme (ws or wss) based on HTTP scheme
    # Check X-Forwarded-Proto header for proxies like Fly.io
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    is_secure = request.url.scheme == "https" or forwarded_proto == "https"
    ws_scheme = "wss" if is_secure else "ws"
    base_url = f"{ws_scheme}://{request.url.netloc}"
    
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
            "stream": f"{base_url}/stream/{{session_code}}",
            "stream_binary": f"{base_url}/stream/binary/{{session_code}}"
        },
        "examples": [
            "Create session: POST /api/sessions/create",
            f"Stream (JSON): {base_url}/stream/swift-neural-42",
            f"Stream (Binary/MessagePack): {base_url}/stream/binary/swift-neural-42",
            f"With filter: {base_url}/stream/swift-neural-42?target_id=0"
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
    lsl_stats = lsl_manager.get_stats() if lsl_manager else {}
    
    return {
        "active_connections": len(active_connections),
        "session_manager": stats,
        "lsl_streaming": lsl_stats
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


async def _handle_stream(
    websocket: WebSocket,
    session_code: str,
    format: Literal['json', 'binary'],
    trial_id: Optional[int] = None,
    target_id: Optional[int] = None
) -> None:
    """
    Generic handler for WebSocket streaming with session isolation.
    
    Args:
        websocket: WebSocket connection
        session_code: Session identifier (e.g., 'swift-neural-42')
        format: Output format ('json' or 'binary')
        trial_id: Optional filter to only stream packets from this trial
        target_id: Optional filter to only stream packets reaching for this target index
    
    Performance comparison (format parameter):
        - 'json': Human-readable, easier debugging, ~15KB packets
        - 'binary': MessagePack format, 60% smaller (~6KB), 3-5x faster serialization
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
    
    # Initialize LSL streamer for this session if enabled
    lsl_streamer = None
    if lsl_manager and settings.lsl_enabled:
        lsl_streamer = lsl_manager.get_streamer(session_code)
        if not lsl_streamer:
            # Create LSL streamer for this session
            metadata = playback_engine.get_metadata()
            lsl_streamer = lsl_manager.create_streamer(session_code, metadata.num_channels)
            if lsl_streamer:
                logger.info(f"LSL streaming enabled for session {session_code}")
    
    client_id = id(websocket)
    format_desc = "binary" if format == "binary" else "JSON"
    logger.info(f"Client {client_id} connected to {format_desc} stream session {session_code}. Active connections: {len(active_connections)}")
    
    try:
        # Send initial metadata
        metadata = playback_engine.get_metadata()
        endpoint = f"/stream/binary/{session_code}" if format == "binary" else f"/stream/{session_code}"
        metadata_msg = {
            "type": "metadata",
            "data": metadata.model_dump(),
            "session": {
                "code": session_code,
                "url": f"ws://localhost:{settings.port}{endpoint}"
            }
        }
        
        if format == "binary":
            binary_metadata = serialize_for_websocket("metadata", metadata_msg["data"])
            await websocket.send_bytes(binary_metadata)
        else:
            await websocket.send_json(metadata_msg)
        
        # Start streaming packets with optional filters
        async for packet in playback_engine.stream(loop=True, trial_filter=trial_id, target_filter=target_id):
            try:
                # Mesurer la latence tick-to-network
                tick_generation_time = packet.timestamp
                
                # Send packet via LSL if enabled
                if lsl_streamer:
                    await lsl_streamer.push_packet_async(packet)
                
                # Send packet in requested format
                if format == "binary":
                    binary_packet = serialize_for_websocket("data", packet)
                    await websocket.send_bytes(binary_packet)
                else:
                    packet_msg = {
                        "type": "data",
                        "data": packet.model_dump()
                    }
                    await websocket.send_json(packet_msg)
                
                # Calculer et enregistrer la latence réseau
                network_send_time = time.time()
                network_latency = network_send_time - tick_generation_time
                playback_engine._network_latencies.append(network_latency)
                
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
                logger.info(f"Client {client_id} disconnected during {format_desc} streaming")
                break
            except Exception as e:
                logger.error(f"Error sending {format_desc} packet to client {client_id}: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from {format_desc} stream session {session_code}")
    except Exception as e:
        logger.error(f"Error in {format_desc} WebSocket connection {client_id} (session {session_code}): {e}")
    finally:
        active_connections.discard(websocket)
        session_manager.decrement_connections(session_code)
        logger.info(f"Client {client_id} removed from {format_desc} stream session {session_code}. Active connections: {len(active_connections)}")


@app.websocket("/stream/{session_code}")
async def websocket_stream(websocket: WebSocket, session_code: str, 
                          trial_id: Optional[int] = None, target_id: Optional[int] = None):
    """
    WebSocket endpoint for 40Hz neural data streaming with session isolation (JSON format).
    
    Path parameters:
        session_code: Session identifier (e.g., 'swift-neural-42')
    
    Query parameters:
        trial_id: Filter to only stream packets from this trial
        target_id: Filter to only stream packets reaching for this target index
    
    Clients connect to ws://localhost:8000/stream/{session_code} to receive real-time
    packets containing time-aligned spike counts and behavioral ground truth in JSON format.
    
    Each session has independent playback state (position, pause, filters).
    
    For better performance, use the binary endpoint: /stream/binary/{session_code}
    """
    await _handle_stream(websocket, session_code, format='json', trial_id=trial_id, target_id=target_id)


@app.websocket("/stream/binary/{session_code}")
async def websocket_stream_binary(websocket: WebSocket, session_code: str, 
                                  trial_id: Optional[int] = None, target_id: Optional[int] = None):
    """
    WebSocket endpoint for 40Hz neural data streaming with session isolation (Binary/MessagePack format).
    
    Path parameters:
        session_code: Session identifier (e.g., 'swift-neural-42')
    
    Query parameters:
        trial_id: Filter to only stream packets from this trial
        target_id: Filter to only stream packets reaching for this target index
    
    Clients connect to ws://localhost:8000/stream/binary/{session_code} to receive real-time
    packets containing time-aligned spike counts and behavioral ground truth in MessagePack binary format.
    
    Performance benefits over JSON endpoint:
    - ~60% smaller payload size (6KB vs 15KB per packet for 142 channels)
    - ~3-5x faster serialization/deserialization
    - Lower CPU overhead for high-frequency streaming
    
    Each session has independent playback state (position, pause, filters).
    """
    await _handle_stream(websocket, session_code, format='binary', trial_id=trial_id, target_id=target_id)


@app.get("/metrics")
async def get_metrics():
    """
    Endpoint de métriques pour le monitoring système.
    
    Expose:
    - Latency tick-to-network par session
    - Memory usage par session
    - Nombre de paquets droppés par session
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    metrics = session_manager.get_metrics()
    
    return {
        "timestamp": time.time(),
        "service": "PhantomLink Core",
        "version": "0.2.0",
        "metrics": metrics
    }


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
