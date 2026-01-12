# Guide des Métriques PhantomLink

## Vue d'ensemble

PhantomLink expose un endpoint `/metrics` qui fournit des métriques détaillées sur les performances du système pour chaque session active.

## Endpoint

```
GET http://localhost:8000/metrics
```

## Format de Réponse

```json
{
  "timestamp": 1705075200.123,
  "service": "PhantomLink Core",
  "version": "0.2.0",
  "metrics": {
    "total_sessions": 2,
    "active_sessions": 1,
    "total_connections": 1,
    "sessions": {
      "swift-neural-42": {
        "packets_sent": 15230,
        "dropped_packets": 3,
        "network_latency_ms": {
          "mean": 1.234,
          "std": 0.456,
          "max": 5.678
        },
        "timing_error_ms": {
          "mean": 0.123,
          "std": 0.089,
          "max": 2.345
        },
        "memory_usage_mb": 12.45,
        "is_running": true,
        "is_paused": false,
        "connections": 1
      }
    }
  }
}
```

## Métriques Disponibles

### Métriques Globales

- **total_sessions**: Nombre total de sessions actives
- **active_sessions**: Nombre de sessions en cours de streaming
- **total_connections**: Nombre total de connexions WebSocket actives

### Métriques par Session

#### 1. Latence Tick-to-Network (`network_latency_ms`)

Mesure le temps écoulé entre la génération d'un paquet de données et son envoi sur le réseau.

- **mean**: Latence moyenne (ms)
- **std**: Écart-type de la latence (ms)
- **max**: Latence maximale observée (ms)

**Interprétation:**
- < 1ms : Excellent
- 1-5ms : Bon
- 5-10ms : Acceptable
- \> 10ms : Problème de performance

#### 2. Utilisation Mémoire (`memory_usage_mb`)

Mémoire utilisée par chaque session en mégaoctets (MB).

**Composants:**
- Objets PlaybackEngine
- Buffers de timing errors
- Buffers de latence réseau

**Limites recommandées:**
- Par session : < 50 MB
- Total système : < 500 MB pour 10 sessions

#### 3. Paquets Droppés (`dropped_packets`)

Nombre de paquets qui n'ont pas pu être envoyés (généralement dû à des problèmes de réseau ou de surcharge).

**Interprétation:**
- 0 : Idéal
- < 0.1% : Acceptable
- \> 1% : Problème critique

#### 4. Erreur de Timing (`timing_error_ms`)

Écart entre le timing prévu (40Hz = 25ms) et le timing réel.

**Interprétation:**
- < 1ms : Excellent (timing précis)
- 1-2ms : Bon
- \> 5ms : Problème de stabilité

## Utilisation

### Python

```python
import requests

response = requests.get('http://localhost:8000/metrics')
metrics = response.json()

# Vérifier la latence moyenne
for session_code, session_metrics in metrics['metrics']['sessions'].items():
    latency = session_metrics['network_latency_ms']['mean']
    print(f"Session {session_code}: {latency:.2f}ms latency")
    
    # Alert si latence élevée
    if latency > 5.0:
        print(f"⚠️ High latency detected in session {session_code}")
```

### cURL

```bash
curl http://localhost:8000/metrics | jq '.metrics.sessions'
```

### Monitoring Continue

```python
import time
import requests

def monitor_metrics(interval_seconds=10):
    """Monitor metrics continuously"""
    while True:
        try:
            response = requests.get('http://localhost:8000/metrics')
            metrics = response.json()
            
            print(f"\n=== Metrics at {time.strftime('%H:%M:%S')} ===")
            print(f"Active Sessions: {metrics['metrics']['active_sessions']}")
            
            for session, data in metrics['metrics']['sessions'].items():
                print(f"\n{session}:")
                print(f"  Packets: {data['packets_sent']} (dropped: {data['dropped_packets']})")
                print(f"  Latency: {data['network_latency_ms']['mean']:.2f}ms")
                print(f"  Memory: {data['memory_usage_mb']:.2f} MB")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(interval_seconds)

# Lancer le monitoring
monitor_metrics()
```

## Intégration avec des Systèmes de Monitoring

### Prometheus

Les métriques peuvent être facilement adaptées au format Prometheus:

```python
from prometheus_client import Gauge, start_http_server
import requests

# Définir les gauges
session_latency = Gauge('phantomlink_session_latency_ms', 
                        'Network latency per session', ['session_code'])
session_memory = Gauge('phantomlink_session_memory_mb', 
                       'Memory usage per session', ['session_code'])
dropped_packets = Gauge('phantomlink_dropped_packets', 
                        'Dropped packets per session', ['session_code'])

def update_prometheus_metrics():
    response = requests.get('http://localhost:8000/metrics')
    metrics = response.json()
    
    for session, data in metrics['metrics']['sessions'].items():
        session_latency.labels(session_code=session).set(
            data['network_latency_ms']['mean']
        )
        session_memory.labels(session_code=session).set(
            data['memory_usage_mb']
        )
        dropped_packets.labels(session_code=session).set(
            data['dropped_packets']
        )
```

### Grafana Dashboard

Créez un dashboard Grafana pour visualiser:

1. **Latence Réseau** : Time series de `network_latency_ms`
2. **Utilisation Mémoire** : Stacked area chart de `memory_usage_mb`
3. **Taux de Perte** : `dropped_packets / packets_sent * 100`
4. **Sessions Actives** : Gauge de `active_sessions`

## Alertes Recommandées

```python
ALERT_THRESHOLDS = {
    'latency_ms': 10.0,           # Latence > 10ms
    'dropped_packets_rate': 0.01,  # > 1% de perte
    'memory_per_session_mb': 50.0, # > 50 MB par session
    'timing_error_ms': 5.0         # Erreur de timing > 5ms
}

def check_alerts(metrics):
    alerts = []
    
    for session, data in metrics['metrics']['sessions'].items():
        # Vérifier latence
        if data['network_latency_ms']['mean'] > ALERT_THRESHOLDS['latency_ms']:
            alerts.append(f"High latency in {session}: {data['network_latency_ms']['mean']:.2f}ms")
        
        # Vérifier mémoire
        if data['memory_usage_mb'] > ALERT_THRESHOLDS['memory_per_session_mb']:
            alerts.append(f"High memory usage in {session}: {data['memory_usage_mb']:.2f} MB")
        
        # Vérifier paquets droppés
        if data['packets_sent'] > 0:
            drop_rate = data['dropped_packets'] / data['packets_sent']
            if drop_rate > ALERT_THRESHOLDS['dropped_packets_rate']:
                alerts.append(f"High packet loss in {session}: {drop_rate*100:.2f}%")
    
    return alerts
```

## Optimisation des Performances

### Réduire la Latence

1. **Désactiver le bruit middleware** en production si non nécessaire
2. **Utiliser MessagePack** (déjà activé par défaut)
3. **Optimiser la taille des buffers** de latence/timing

### Réduire l'Utilisation Mémoire

1. **Limiter la taille des buffers** de métriques (1000 derniers échantillons)
2. **Nettoyer les sessions inactives** régulièrement
3. **Ajuster `session_ttl`** dans la configuration

### Réduire les Paquets Droppés

1. **Augmenter la capacité réseau**
2. **Limiter le nombre de sessions simultanées**
3. **Monitorer la charge CPU/Network**

## Troubleshooting

### Latence Élevée

```bash
# Vérifier la charge système
curl http://localhost:8000/metrics | jq '.metrics.sessions[].network_latency_ms'

# Vérifier les erreurs de timing
curl http://localhost:8000/metrics | jq '.metrics.sessions[].timing_error_ms'
```

### Fuite Mémoire

```bash
# Surveiller l'évolution de la mémoire
watch -n 1 'curl -s http://localhost:8000/metrics | jq ".metrics.sessions[].memory_usage_mb"'
```

### Paquets Droppés

```bash
# Vérifier le taux de perte
curl http://localhost:8000/metrics | jq '.metrics.sessions[] | 
  {session, dropped: .dropped_packets, sent: .packets_sent, 
   rate: (.dropped_packets / .packets_sent * 100)}'
```

## Bonnes Pratiques

1. **Monitoring régulier** : Interroger `/metrics` toutes les 10-30 secondes
2. **Historisation** : Stocker les métriques pour analyse de tendances
3. **Alertes proactives** : Configurer des seuils d'alerte appropriés
4. **Nettoyage** : Supprimer les sessions inactives pour libérer la mémoire
5. **Capacity planning** : Utiliser les métriques pour dimensionner l'infrastructure

## Référence API Complète

| Métrique | Type | Description | Unité |
|----------|------|-------------|-------|
| `timestamp` | float | Horodatage de la réponse | Unix timestamp |
| `total_sessions` | int | Nombre de sessions actives | count |
| `active_sessions` | int | Sessions en streaming | count |
| `total_connections` | int | Connexions WebSocket | count |
| `packets_sent` | int | Paquets envoyés | count |
| `dropped_packets` | int | Paquets perdus | count |
| `network_latency_ms.mean` | float | Latence moyenne | milliseconds |
| `network_latency_ms.std` | float | Écart-type latence | milliseconds |
| `network_latency_ms.max` | float | Latence max | milliseconds |
| `timing_error_ms.mean` | float | Erreur timing moyenne | milliseconds |
| `timing_error_ms.std` | float | Écart-type timing | milliseconds |
| `timing_error_ms.max` | float | Erreur timing max | milliseconds |
| `memory_usage_mb` | float | Mémoire utilisée | megabytes |
| `is_running` | bool | Session active | boolean |
| `is_paused` | bool | Session en pause | boolean |
| `connections` | int | Connexions actives | count |
