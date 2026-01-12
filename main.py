"""
PhantomLink Core - BCI Mock Server

Entry point for running the server.

📖 Documentation: See README.md (single source of truth)
"""
import uvicorn
from phantomlink.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "phantomlink.server:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False
    )
