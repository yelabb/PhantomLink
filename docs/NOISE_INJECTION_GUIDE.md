# Guide d'Utilisation - Middleware d'Injection de Bruit

## 🎯 Objectif

Le `NoiseInjectionMiddleware` transforme PhantomLink d'un simple lecteur de données en **simulateur de stress-test** pour évaluer la robustesse des décodeurs neuronaux dans des conditions de production réalistes.

## 🔬 Pourquoi l'Injection de Bruit ?

**Problème** : Les données neuronales réelles en production sont "sales" :
- Bruit thermique et électrique
- Fatigue neuronale au fil du temps
- Micro-mouvements de l'implant
- Variations non-stationnaires

**Conséquence** : Un décodeur entraîné sur des données parfaites échouera en conditions réelles.

**Solution** : Injecter du bruit réaliste pendant le développement pour garantir la robustesse.

---

## 🚀 Utilisation Rapide

### Installation

Aucune dépendance supplémentaire n'est requise. Le middleware est inclus dans PhantomLink.

### Exemple de Base

```python
from pathlib import Path
from phantomlink.playback_engine import PlaybackEngine, NoiseInjectionMiddleware
from phantomlink.config import settings

# 1. Créer le middleware
middleware = NoiseInjectionMiddleware(
    noise_std=0.5,              # Bruit gaussien modéré
    drift_amplitude=0.3,         # Dérive de 30%
    drift_period_seconds=60.0,   # Cycle de fatigue sur 60s
    enable_noise=True,
    enable_drift=True
)

# 2. Créer l'engine avec le middleware
data_path = Path(settings.data_dir) / f"{settings.dataset_name}.nwb"
engine = PlaybackEngine(data_path, noise_middleware=middleware)

# 3. Utiliser normalement
await engine.initialize()
async for packet in engine.stream():
    # Les packets contiennent maintenant des données bruitées
    spike_counts = packet.spikes.spike_counts
    # ... votre code de décodage ...
```

---

## ⚙️ Configuration

### Paramètres du Middleware

| Paramètre | Type | Description | Valeur par défaut |
|-----------|------|-------------|-------------------|
| `noise_std` | float | Écart-type du bruit gaussien (proportion du signal) | 0.5 |
| `drift_amplitude` | float | Amplitude de la dérive (proportion du signal) | 0.2 |
| `drift_period_seconds` | float | Période de la dérive en secondes | 60.0 |
| `enable_noise` | bool | Active/désactive le bruit blanc | True |
| `enable_drift` | bool | Active/désactive la dérive | True |

### Niveaux de Stress Recommandés

#### 🟢 Léger (Light)
```python
middleware = NoiseInjectionMiddleware(
    noise_std=0.2,
    drift_amplitude=0.1
)
```
**Usage** : Validation de base, test de sanity

#### 🟡 Modéré (Moderate) - RECOMMANDÉ
```python
middleware = NoiseInjectionMiddleware(
    noise_std=0.5,
    drift_amplitude=0.3
)
```
**Usage** : Conditions de production réalistes

#### 🟠 Intense (Intense)
```python
middleware = NoiseInjectionMiddleware(
    noise_std=1.0,
    drift_amplitude=0.5
)
```
**Usage** : Scénarios difficiles, conditions dégradées

#### 🔴 Extrême (Extreme)
```python
middleware = NoiseInjectionMiddleware(
    noise_std=2.0,
    drift_amplitude=0.8
)
```
**Usage** : Stress-test aux limites, test de failure

---

## 📊 Comparaison avec/sans Bruit

### Exécuter la Démo

```bash
python examples/noise_injection_demo.py
```

Cette démo génère :
1. **Comparaison superposée** : Données propres vs bruitées
2. **Analyse statistique** : Changements de variance et moyenne
3. **Niveaux de stress** : Visualisation de 4 niveaux d'intensité

Graphiques sauvegardés :
- `noise_injection_comparison.png`
- `stress_levels_comparison.png`

---

## 🧪 Tests

### Lancer les Tests Unitaires

```bash
# Tests complets
pytest tests/test_noise_injection.py -v

# Ou via le script
python scripts/test_noise_middleware.py
```

### Tests Inclus

- ✅ Initialisation et configuration
- ✅ Injection de bruit gaussien
- ✅ Injection de dérive non-stationnaire
- ✅ Contrainte de non-négativité
- ✅ Reset d'état
- ✅ Variation par canal
- ✅ Préservation des métadonnées
- ✅ Intégration avec PlaybackEngine

---

## 🎓 Cas d'Usage

### 1. Test de Robustesse d'un Décodeur

```python
# Entraînement sur données propres
clean_engine = PlaybackEngine(data_path)
decoder = train_decoder(clean_engine)

# Test sur données bruitées
noisy_middleware = NoiseInjectionMiddleware(noise_std=0.5, drift_amplitude=0.3)
noisy_engine = PlaybackEngine(data_path, noise_middleware=noisy_middleware)

# Évaluer la dégradation de performance
clean_accuracy = evaluate(decoder, clean_engine)
noisy_accuracy = evaluate(decoder, noisy_engine)

print(f"Dégradation: {(1 - noisy_accuracy/clean_accuracy) * 100:.1f}%")
```

### 2. Entraînement avec Augmentation de Données

```python
# Entraîner avec du bruit pour améliorer la généralisation
middleware = NoiseInjectionMiddleware(noise_std=0.3, drift_amplitude=0.2)
engine = PlaybackEngine(data_path, noise_middleware=middleware)

decoder = train_decoder(engine)  # Décodeur plus robuste
```

### 3. Benchmark Comparatif

```python
# Comparer plusieurs décodeurs sous stress
stress_levels = [
    ("Clean", None),
    ("Light", NoiseInjectionMiddleware(0.2, 0.1)),
    ("Moderate", NoiseInjectionMiddleware(0.5, 0.3)),
    ("Intense", NoiseInjectionMiddleware(1.0, 0.5))
]

results = {}
for level_name, middleware in stress_levels:
    engine = PlaybackEngine(data_path, noise_middleware=middleware)
    results[level_name] = {
        "decoder_A": evaluate(decoder_A, engine),
        "decoder_B": evaluate(decoder_B, engine)
    }

# Identifier le décodeur le plus robuste
```

### 4. Simulation de Scénarios Cliniques

```python
# Simuler la fatigue d'un patient sur une longue session
fatigue_middleware = NoiseInjectionMiddleware(
    noise_std=0.4,
    drift_amplitude=0.5,
    drift_period_seconds=120.0  # Fatigue progressive sur 2 minutes
)

engine = PlaybackEngine(data_path, noise_middleware=fatigue_middleware)
# Évaluer la performance au fil du temps
```

---

## 🔍 Détails Techniques

### Modèle de Bruit

Le middleware applique deux types de corruption :

#### 1. Bruit Blanc Gaussien
```
spike_counts_noisy = spike_counts + N(0, σ) * (spike_counts + 1)
```
- **Proportionnel au signal** : Plus le taux de décharge est élevé, plus le bruit est important
- **Indépendant dans le temps** : Pas de corrélation temporelle

#### 2. Dérive Non-Stationnaire
```
drift = A * [sin(2π * t / T_slow) + 0.1 * sin(2π * t / T_fast)] * (spike_counts + 1) * (1 + offset_per_channel)
```
- **Composante lente** : Simule la fatigue neuronale (période `drift_period_seconds`)
- **Composante rapide** : Simule le micro-mouvement de l'implant (période / 10)
- **Variation par canal** : Chaque canal a une dérive légèrement différente

### Garanties

- ✅ **Non-négativité** : `spike_counts >= 0` toujours respecté
- ✅ **Préservation des métadonnées** : Timestamp, trial_id, kinematics inchangés
- ✅ **Reproductibilité** : Seed aléatoire peut être fixé si nécessaire
- ✅ **Zero overhead** : Si désactivé (`enable_noise=False, enable_drift=False`)

---

## 📈 Configuration via Variables d'Environnement

Vous pouvez également configurer le middleware via `config.py` :

```python
# src/phantomlink/config.py
class Settings(BaseSettings):
    # Noise Injection Configuration
    noise_injection_enabled: bool = False  # Active par défaut
    noise_std: float = 0.5
    drift_amplitude: float = 0.2
    drift_period_seconds: float = 60.0
```

Variables d'environnement :
```bash
export PHANTOM_NOISE_INJECTION_ENABLED=true
export PHANTOM_NOISE_STD=0.5
export PHANTOM_DRIFT_AMPLITUDE=0.3
export PHANTOM_DRIFT_PERIOD_SECONDS=60.0
```

---

## ⚠️ Limitations

1. **Modèle de Bruit Simplifié** : Bruit gaussien + dérive sinusoïdale. Pas de modèle biophysique complexe.
2. **Pas de Corrélation Spatiale** : Chaque canal est bruité indépendamment (pas de bruit corrélé entre canaux).
3. **Pas de Bruit Impulsionnel** : Pas de simulation de "spike artifacts" ou d'interférences électromagnétiques.
4. **Dérive Déterministe** : La dérive suit un pattern sinusoïdal (pas de random walk).

Ces limitations sont volontaires pour garder le middleware simple et rapide.

---

## 💡 Bonnes Pratiques

1. **Commencez léger** : Testez d'abord avec `noise_std=0.2` et augmentez progressivement
2. **Mesurez l'impact** : Quantifiez toujours la dégradation de performance
3. **Documentez vos niveaux** : Notez les paramètres utilisés pour la reproductibilité
4. **Comparez avec baseline** : Toujours évaluer sur données propres d'abord
5. **Adaptez au contexte** : Les niveaux de bruit réels varient selon le type d'implant

---

## 🆘 Support

- **Issues GitHub** : [https://github.com/yelabb/PhantomLink/issues](https://github.com/yelabb/PhantomLink/issues)
- **Documentation** : [README.md](../README.md)
- **Exemples** : [examples/noise_injection_demo.py](../examples/noise_injection_demo.py)
- **Tests** : [tests/test_noise_injection.py](../tests/test_noise_injection.py)

---

## 📚 Références

- **Neural Noise Models** : Churchland et al., Nature Neuroscience 2010
- **BCI Robustness** : Jarosiewicz et al., Journal of Neural Engineering 2015
- **Non-Stationarity** : Perge et al., Journal of Neurophysiology 2013
