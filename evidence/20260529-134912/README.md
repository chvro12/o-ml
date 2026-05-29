# Mesures Minikube - 2026-05-29

Contexte :

- Cas 2 : moderation de commentaires toxiques.
- Cluster local : Minikube avec driver Docker.
- Namespace : `projet-pst`.
- URL de test : `http://127.0.0.1:18080/predict` via `kubectl port-forward`.
- Images Docker Hub : tag `1.0.0`, publiees en multi-architecture `linux/amd64` et `linux/arm64`.

Resultats :

| Niveau | Rate | Requetes | HTTP 200 | Succes | Moyenne | P95 | Max | Restarts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nominal | 10 req/min | 50 | 50 | 100.0 % | 0.059 s | 0.082 s | 0.105 s | 0 |
| Charge | 50 req/min | 250 | 250 | 100.0 % | 0.051 s | 0.078 s | 0.308 s | 0 |
| Stress | 150 req/min | 744 | 744 | 100.0 % | 0.042 s | 0.061 s | 0.175 s | 0 |

Conclusion :

Le deploiement respecte le quota Kubernetes du cas 2 et la contrainte de latence.
Le P95 reste sous 500 ms sur les trois niveaux, y compris le stress impose.
Aucun pod n'a redemarre pendant les mesures.

Fichiers principaux :

- `nominal-load-test.txt`, `charge-load-test.txt`, `stress-load-test.txt` :
  sorties completes des tests de charge.
- `quota-before.txt` : quota Kubernetes observe.
- `*-top-before.txt`, `*-top-after.txt`, `*-top-every-30s.txt` :
  consommation CPU/RAM.
- `*-metrics.txt` : metriques exposees par le service monitoring.
- `cluster-get-all-before.txt`, `cluster-get-all-after.txt` :
  etat du namespace avant et apres les mesures.
