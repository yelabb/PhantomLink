"""
Tests pour le middleware d'injection de bruit.
"""
import pytest
import numpy as np
from pathlib import Path

from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware
from phantomlink.models import StreamPacket, SpikeData, Kinematics, TargetIntention
from phantomlink.config import settings


def create_test_packet(spike_counts=None):
    """Crée un paquet de test."""
    if spike_counts is None:
        spike_counts = [10, 15, 20, 25, 30]  # 5 canaux
    
    return StreamPacket(
        timestamp=1234567890.0,
        sequence_number=42,
        spikes=SpikeData(
            channel_ids=list(range(len(spike_counts))),
            spike_counts=spike_counts,
            bin_size_ms=25.0
        ),
        kinematics=Kinematics(vx=0.1, vy=0.2, x=10.0, y=20.0),
        intention=TargetIntention(target_id=1, target_x=15.0, target_y=25.0),
        trial_id=1,
        trial_time_ms=1000.0
    )


class TestNoiseInjectionMiddleware:
    """Tests pour NoiseInjectionMiddleware."""
    
    def test_initialization(self):
        """Test l'initialisation du middleware."""
        middleware = NoiseInjectionMiddleware(
            noise_std=0.5,
            drift_amplitude=0.3,
            drift_period_seconds=60.0
        )
        
        assert middleware.noise_std == 0.5
        assert middleware.drift_amplitude == 0.3
        assert middleware.drift_period_seconds == 60.0
        assert middleware.enable_noise is True
        assert middleware.enable_drift is True
    
    def test_disabled_middleware_returns_original(self):
        """Test que le middleware désactivé retourne le paquet original."""
        middleware = NoiseInjectionMiddleware(
            enable_noise=False,
            enable_drift=False
        )
        
        original = create_test_packet()
        result = middleware.inject_noise(original, elapsed_time=0.0)
        
        assert result.spikes.spike_counts == original.spikes.spike_counts
    
    def test_noise_injection_changes_values(self):
        """Test que l'injection de bruit modifie les valeurs."""
        middleware = NoiseInjectionMiddleware(
            noise_std=0.5,
            enable_noise=True,
            enable_drift=False
        )
        
        original = create_test_packet([10] * 10)  # 10 canaux identiques
        result = middleware.inject_noise(original, elapsed_time=0.0)
        
        # Les valeurs doivent être différentes
        assert result.spikes.spike_counts != original.spikes.spike_counts
        
        # Mais la moyenne doit rester proche
        mean_diff = abs(np.mean(result.spikes.spike_counts) - np.mean(original.spikes.spike_counts))
        assert mean_diff < 2.0  # Tolérance raisonnable
    
    def test_noise_increases_variance(self):
        """Test que le bruit augmente la variance."""
        middleware = NoiseInjectionMiddleware(
            noise_std=1.0,
            enable_noise=True,
            enable_drift=False
        )
        
        original = create_test_packet([20] * 20)  # Signal constant
        result = middleware.inject_noise(original, elapsed_time=0.0)
        
        # La variance doit augmenter significativement
        original_std = np.std(original.spikes.spike_counts)
        result_std = np.std(result.spikes.spike_counts)
        
        assert result_std > original_std
    
    def test_drift_creates_temporal_pattern(self):
        """Test que la dérive crée un pattern temporel."""
        middleware = NoiseInjectionMiddleware(
            noise_std=0.0,  # Pas de bruit
            drift_amplitude=0.5,
            drift_period_seconds=10.0,
            enable_noise=False,
            enable_drift=True
        )
        
        original = create_test_packet([20] * 5)
        
        # Collecter plusieurs valeurs à différents temps
        values_over_time = []
        for t in np.linspace(0, 20, 50):  # 2 périodes
            result = middleware.inject_noise(original, elapsed_time=t)
            values_over_time.append(np.mean(result.spikes.spike_counts))
        
        # La dérive doit créer une variation
        std_over_time = np.std(values_over_time)
        assert std_over_time > 1.0  # Il doit y avoir une variation significative
    
    def test_non_negative_constraint(self):
        """Test que les spike counts restent non-négatifs."""
        middleware = NoiseInjectionMiddleware(
            noise_std=5.0,  # Bruit très élevé
            drift_amplitude=2.0,  # Dérive très élevée
            enable_noise=True,
            enable_drift=True
        )
        
        # Créer un paquet avec de faibles valeurs
        original = create_test_packet([1, 2, 3, 0, 1])
        
        # Tester sur plusieurs temps pour capturer différentes dérives
        for t in np.linspace(0, 100, 20):
            result = middleware.inject_noise(original, elapsed_time=t)
            
            # Tous les spike counts doivent être >= 0
            assert all(count >= 0 for count in result.spikes.spike_counts)
    
    def test_reset_functionality(self):
        """Test que le reset réinitialise l'état."""
        middleware = NoiseInjectionMiddleware(
            drift_amplitude=0.5,
            enable_drift=True
        )
        
        original = create_test_packet()
        
        # Premier appel initialise l'état
        result1 = middleware.inject_noise(original, elapsed_time=10.0)
        assert middleware._drift_offset is not None
        assert middleware._time_start is not None
        
        # Reset
        middleware.reset()
        assert middleware._drift_offset is None
        assert middleware._time_start is None
        
        # Deuxième appel réinitialise avec de nouvelles valeurs
        result2 = middleware.inject_noise(original, elapsed_time=10.0)
        # Les résultats peuvent être différents en raison du nouveau random state
    
    def test_per_channel_drift_variation(self):
        """Test que différents canaux ont des dérives différentes."""
        middleware = NoiseInjectionMiddleware(
            noise_std=0.0,
            drift_amplitude=1.0,
            enable_noise=False,
            enable_drift=True
        )
        
        # Créer un paquet avec des valeurs identiques pour tous les canaux
        original = create_test_packet([10] * 100)
        result = middleware.inject_noise(original, elapsed_time=5.0)
        
        # Après dérive, les canaux doivent avoir des valeurs différentes
        unique_values = len(set(result.spikes.spike_counts))
        assert unique_values > 1  # Pas tous identiques
    
    def test_metadata_preservation(self):
        """Test que les métadonnées du paquet sont préservées."""
        middleware = NoiseInjectionMiddleware(
            noise_std=0.5,
            drift_amplitude=0.2
        )
        
        original = create_test_packet()
        result = middleware.inject_noise(original, elapsed_time=1.0)
        
        # Vérifier que les métadonnées sont préservées
        assert result.timestamp == original.timestamp
        assert result.sequence_number == original.sequence_number
        assert result.trial_id == original.trial_id
        assert result.trial_time_ms == original.trial_time_ms
        assert result.kinematics == original.kinematics
        assert result.intention == original.intention
        assert result.spikes.channel_ids == original.spikes.channel_ids
        assert result.spikes.bin_size_ms == original.spikes.bin_size_ms


@pytest.mark.asyncio
async def test_integration_with_playback_engine():
    """Test l'intégration avec PlaybackEngine."""
    # Créer le middleware
    middleware = NoiseInjectionMiddleware(
        noise_std=0.3,
        drift_amplitude=0.2,
        enable_noise=True,
        enable_drift=True
    )
    
    # Créer l'engine avec le middleware
    data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
    
    if not data_path.exists():
        pytest.skip(f"Dataset not found at {data_path}")
    
    engine = PlaybackEngine(data_path, noise_middleware=middleware)
    await engine.initialize()
    
    # Stream quelques paquets
    packets = []
    async for packet in engine.stream(loop=False):
        packets.append(packet)
        if len(packets) >= 10:
            break
    
    engine.stop()
    
    # Vérifier que nous avons reçu des paquets
    assert len(packets) == 10
    
    # Vérifier que les paquets ont été modifiés (variance > 0)
    all_counts = []
    for packet in packets:
        all_counts.extend(packet.spikes.spike_counts)
    
    assert np.std(all_counts) > 0


@pytest.mark.asyncio
async def test_middleware_reset_on_loop():
    """Test que le middleware est reset quand le stream boucle."""
    middleware = NoiseInjectionMiddleware(
        drift_amplitude=0.5,
        enable_drift=True
    )
    
    data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
    
    if not data_path.exists():
        pytest.skip(f"Dataset not found at {data_path}")
    
    engine = PlaybackEngine(data_path, noise_middleware=middleware)
    await engine.initialize()
    
    # Le middleware doit initialiser son état lors du premier paquet
    packet_count = 0
    async for packet in engine.stream(loop=False):
        packet_count += 1
        if packet_count == 1:
            assert middleware._drift_offset is not None
            first_offset = middleware._drift_offset.copy()
        if packet_count >= 5:
            break
    
    engine.stop()
    
    # Reset manuel
    engine.reset()
    assert middleware._drift_offset is None


def test_different_noise_levels():
    """Test avec différents niveaux de bruit."""
    original = create_test_packet([20] * 10)
    
    noise_levels = [0.1, 0.5, 1.0, 2.0]
    variances = []
    
    for noise_std in noise_levels:
        middleware = NoiseInjectionMiddleware(
            noise_std=noise_std,
            enable_noise=True,
            enable_drift=False
        )
        
        # Générer plusieurs échantillons
        samples = []
        for _ in range(100):
            result = middleware.inject_noise(original, elapsed_time=0.0)
            samples.append(np.mean(result.spikes.spike_counts))
        
        variances.append(np.var(samples))
    
    # La variance doit augmenter avec le niveau de bruit
    for i in range(len(variances) - 1):
        assert variances[i] < variances[i + 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
