"""
FastAPI server with WebSocket streaming endpoint.

This module implements the REST and WebSocket API for PhantomLink Core.
"""
import logging
from pathlib import Path
from typing import Set
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import StreamMetadata
from playback_engine import PlaybackEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PhantomLink Core",
    description="BCI Mock Server - The Ethereal/Mailtrap for Neurotechnology",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global playback engine instance
playback_engine: PlaybackEngine = None
active_connections: Set[WebSocket] = set()


@app.on_event("startup")
async def startup_event():
    """Initialize the playback engine on startup."""
    global playback_engine
    
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
    
    # Initialize playback engine
    playback_engine = PlaybackEngine(dataset_path)
    await playback_engine.initialize()
    
    logger.info(f"Server ready on {settings.host}:{settings.port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global playback_engine
    
    logger.info("Shutting down PhantomLink Core server")
    
    # Stop all active streams
    if playback_engine:
        playback_engine.stop()
        await playback_engine.cleanup()
    
    # Close all WebSocket connections
    for connection in active_connections:
        await connection.close()
    
    logger.info("Server shutdown complete")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "PhantomLink Core",
        "version": "0.1.0",
        "description": "BCI Mock Server for Neurotechnology Development",
        "endpoints": {
            "metadata": "/api/metadata",
            "stats": "/api/stats",
            "control": "/api/control",
            "stream": "ws://localhost:8000/stream"
        }
    }


@app.get("/api/metadata")
async def get_metadata():
    """Get metadata about the current dataset and stream configuration."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    metadata = playback_engine.get_metadata()
    return metadata


@app.get("/api/stats")
async def get_stats():
    """Get current playback statistics."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    stats = playback_engine.get_stats()
    return {
        "active_connections": len(active_connections),
        "playback": stats
    }


@app.post("/api/control/pause")
async def pause_playback():
    """Pause the playback."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    playback_engine.pause()
    return {"status": "paused"}


@app.post("/api/control/resume")
async def resume_playback():
    """Resume the playback."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    playback_engine.resume()
    return {"status": "resumed"}


@app.post("/api/control/stop")
async def stop_playback():
    """Stop the playback."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    playback_engine.stop()
    return {"status": "stopped"}


@app.post("/api/control/seek")
async def seek_playback(position_seconds: float):
    """Seek to a specific position in the dataset."""
    if not playback_engine:
        raise HTTPException(status_code=503, detail="Playback engine not initialized")
    
    playback_engine.seek(position_seconds)
    return {"status": "seeked", "position_seconds": position_seconds}


@app.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for 40Hz neural data streaming.
    
    Clients connect to ws://localhost:8000/stream to receive real-time
    packets containing time-aligned spike counts and behavioral ground truth.
    """
    await websocket.accept()
    active_connections.add(websocket)
    
    client_id = id(websocket)
    logger.info(f"Client {client_id} connected. Active connections: {len(active_connections)}")
    
    try:
        # Send initial metadata
        metadata = playback_engine.get_metadata()
        await websocket.send_json({
            "type": "metadata",
            "data": metadata.model_dump()
        })
        
        # Start streaming packets
        async for packet in playback_engine.stream(loop=True):
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
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection {client_id}: {e}")
    finally:
        active_connections.discard(websocket)
        logger.info(f"Client {client_id} removed. Active connections: {len(active_connections)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "engine_initialized": playback_engine is not None,
        "active_connections": len(active_connections)
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
