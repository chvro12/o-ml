# Validation locale du pipeline texte

Cette validation vérifie le fonctionnement applicatif des trois APIs, du
modèle texte entraîné et du script de charge avant les mesures Kubernetes
officielles.

Exécution locale du 27 mai 2026 après chargement du modèle :

```bash
python scripts/load_test.py --case text --level stress --duration 3 \
  --url http://127.0.0.1:18001/predict
```

| Rate configuré | Durée | Requêtes | HTTP 200 | Succès | Moyenne | P95 | Maximum |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 150 req/min | 3 s | 8 | 8 | 100.0 % | 0.046 s | 0.033 s | 0.204 s |

Le monitoring a exposé `inference_requests_total 8`,
`inference_errors_total 0` et huit prédictions structurées. Les valeurs du
challenge officiel de cinq minutes seront consignées dans `STRESS_TEST.md`
après exécution Minikube.

```bash
curl http://127.0.0.1:8002/metrics
curl http://127.0.0.1:8002/predictions
```
