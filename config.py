"""
Configuration settings for PhantomLink Core.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Streaming Configuration
    stream_frequency_hz: int = 40  # 40Hz = 25ms per packet
    packet_interval_ms: float = 25.0  # Derived: 1000ms / 40Hz
    
    # Data Configuration
    data_dir: str = "data"
    dataset_name: str = "mc_maze"
    
    # Performance
    max_connections: int = 10
    buffer_size: int = 100  # Number of packets to pre-buffer
    
    class Config:
        env_prefix = "PHANTOM_"


settings = Settings()
