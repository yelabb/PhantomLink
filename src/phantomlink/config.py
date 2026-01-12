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
    data_dir: str = "data/raw"
    dataset_name: str = "mc_maze"
    
    # Performance
    max_connections: int = 10
    buffer_size: int = 100  # Number of packets to pre-buffer
    
    # LSL Configuration
    lsl_enabled: bool = True  # Enable LSL streaming alongside WebSocket
    lsl_stream_name: str = "PhantomLink-Neural"
    lsl_stream_type: str = "EEG"  # Stream type for LSL
    lsl_source_id: str = "PhantomLink-001"
    
    # Noise Injection Configuration (pour simulation réaliste)
    noise_injection_enabled: bool = False  # Active l'injection de bruit par défaut
    noise_std: float = 0.5  # Écart-type du bruit blanc gaussien
    drift_amplitude: float = 0.2  # Amplitude de la dérive non-stationnaire
    drift_period_seconds: float = 60.0  # Période de la dérive (fatigue neuronale)
    
    class Config:
        env_prefix = "PHANTOM_"


settings = Settings()
