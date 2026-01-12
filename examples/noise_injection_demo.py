"""
Exemple d'utilisation du middleware d'injection de bruit.

Démontre comment activer le "mode stress-test" pour simuler des conditions
de production réalistes avec du bruit et de la dérive.
"""
import asyncio
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware
from phantomlink.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_without_noise():
    """Démo avec données propres (mode par défaut)."""
    logger.info("=== DEMO: Données propres (sans bruit) ===")
    
    data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
    engine = PlaybackEngine(data_path)
    await engine.initialize()
    
    # Collecter quelques paquets
    packets = []
    async for packet in engine.stream(loop=False):
        packets.append(packet)
        if len(packets) >= 100:  # 2.5 secondes de données
            break
    
    engine.stop()
    
    # Extraire spike counts du premier canal
    spike_counts = [p.spikes.spike_counts[0] for p in packets]
    
    return spike_counts


async def demo_with_noise():
    """Démo avec injection de bruit (mode stress-test)."""
    logger.info("=== DEMO: Données bruitées (mode stress-test) ===")
    
    # Créer le middleware d'injection de bruit
    noise_middleware = NoiseInjectionMiddleware(
        noise_std=0.5,              # Bruit gaussien modéré
        drift_amplitude=0.3,         # Dérive de 30%
        drift_period_seconds=30.0,   # Dérive sur 30 secondes
        enable_noise=True,
        enable_drift=True
    )
    
    data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
    engine = PlaybackEngine(data_path, noise_middleware=noise_middleware)
    await engine.initialize()
    
    # Collecter quelques paquets
    packets = []
    async for packet in engine.stream(loop=False):
        packets.append(packet)
        if len(packets) >= 100:  # 2.5 secondes de données
            break
    
    engine.stop()
    
    # Extraire spike counts du premier canal
    spike_counts = [p.spikes.spike_counts[0] for p in packets]
    
    return spike_counts


async def demo_comparison():
    """Compare les données propres vs bruitées."""
    logger.info("\n" + "="*60)
    logger.info("COMPARAISON: Données propres vs Données bruitées")
    logger.info("="*60 + "\n")
    
    # Obtenir les deux versions
    clean_data = await demo_without_noise()
    noisy_data = await demo_with_noise()
    
    # Statistiques
    logger.info("\n📊 Statistiques:")
    logger.info(f"  Données propres - Moyenne: {np.mean(clean_data):.2f}, Std: {np.std(clean_data):.2f}")
    logger.info(f"  Données bruitées - Moyenne: {np.mean(noisy_data):.2f}, Std: {np.std(noisy_data):.2f}")
    logger.info(f"  Augmentation du bruit: {(np.std(noisy_data) / np.std(clean_data) - 1) * 100:.1f}%")
    
    # Visualisation
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    
    # Plot 1: Données propres
    ax1.plot(clean_data, color='#2ecc71', linewidth=2, label='Propres')
    ax1.set_title('Données Propres (mode par défaut)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Spike Count', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Données bruitées
    ax2.plot(noisy_data, color='#e74c3c', linewidth=2, label='Bruitées (stress-test)')
    ax2.set_title('Données Bruitées (avec bruit blanc + dérive)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Spike Count', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Comparaison superposée
    ax3.plot(clean_data, color='#2ecc71', linewidth=2, alpha=0.7, label='Propres')
    ax3.plot(noisy_data, color='#e74c3c', linewidth=2, alpha=0.7, label='Bruitées')
    ax3.set_title('Comparaison Superposée', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Temps (bins de 25ms)', fontsize=12)
    ax3.set_ylabel('Spike Count', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig('noise_injection_comparison.png', dpi=150, bbox_inches='tight')
    logger.info(f"\n📈 Graphique sauvegardé: noise_injection_comparison.png")
    plt.show()


async def demo_stress_levels():
    """Démontre différents niveaux de stress."""
    logger.info("\n" + "="*60)
    logger.info("DEMO: Différents niveaux de stress")
    logger.info("="*60 + "\n")
    
    stress_levels = [
        ("Léger", 0.2, 0.1),
        ("Modéré", 0.5, 0.3),
        ("Intense", 1.0, 0.5),
        ("Extrême", 2.0, 0.8)
    ]
    
    data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, (level_name, noise_std, drift_amp) in enumerate(stress_levels):
        logger.info(f"  Test niveau: {level_name} (noise={noise_std}, drift={drift_amp})")
        
        # Créer middleware avec ce niveau
        middleware = NoiseInjectionMiddleware(
            noise_std=noise_std,
            drift_amplitude=drift_amp,
            drift_period_seconds=20.0,
            enable_noise=True,
            enable_drift=True
        )
        
        engine = PlaybackEngine(data_path, noise_middleware=middleware)
        await engine.initialize()
        
        # Collecter données
        packets = []
        async for packet in engine.stream(loop=False):
            packets.append(packet)
            if len(packets) >= 80:
                break
        
        engine.stop()
        
        # Extraire et tracer
        spike_counts = [p.spikes.spike_counts[0] for p in packets]
        
        axes[idx].plot(spike_counts, linewidth=2)
        axes[idx].set_title(f'Niveau: {level_name}', fontsize=12, fontweight='bold')
        axes[idx].set_ylabel('Spike Count')
        axes[idx].grid(True, alpha=0.3)
        axes[idx].text(0.02, 0.98, f'σ={noise_std}, drift={drift_amp}', 
                      transform=axes[idx].transAxes, 
                      fontsize=10, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('stress_levels_comparison.png', dpi=150, bbox_inches='tight')
    logger.info(f"\n📈 Graphique sauvegardé: stress_levels_comparison.png")
    plt.show()


async def main():
    """Point d'entrée principal."""
    try:
        # Demo 1: Comparaison de base
        await demo_comparison()
        
        # Demo 2: Différents niveaux de stress
        await demo_stress_levels()
        
        logger.info("\n" + "="*60)
        logger.info("✅ Démos terminées avec succès!")
        logger.info("="*60)
        logger.info("\n💡 Conseil: Utilisez le middleware pour stress-tester vos décodeurs")
        logger.info("   et garantir leur robustesse en conditions de production réelles.\n")
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
