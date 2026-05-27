# Challenge de charge - moderation textuelle

## Protocole

```bash
URL="$(minikube service inference-svc -n projet-pst --url)/predict"
python scripts/load_test.py --case text --level nominal --url "$URL"
python scripts/load_test.py --case text --level charge --url "$URL"
python scripts/load_test.py --case text --level stress --url "$URL"
```

Pendant `charge` et `stress`, `scripts/run_challenge.sh "$URL"` enregistre les
sorties de charge, les metriques du monitoring, les predictions et
`kubectl top pods` toutes les 30 secondes.

## Mesures obligatoires

| Niveau | Rate req/min | Requetes | HTTP 200 | Succes | Latence moyenne | P95 | Restarts | Preuve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Nominal | 10 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | `evidence/nominal-*` |
| Charge | 50 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | `evidence/charge-*` |
| Stress | 150 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | `evidence/stress-*` |

## Correction avant et apres

Le critere metier specifique au cas texte est un P95 inferieur a `500 ms`. La
correction doit etre choisie a partir du premier niveau qui depasse ce seuil ou
montre une saturation CPU. Si `model-svc` est proche de `1500m`, la premiere
hypothese a mesurer est le nombre de workers ou la taille du vocabulaire TF-IDF.

| Test relance | Configuration avant | P95 avant | Configuration apres | P95 apres | Succes apres | Conclusion |
| --- | --- | ---: | --- | ---: | ---: | --- |
| Niveau problematique | A mesurer | A mesurer | A definir | A mesurer | A mesurer | A rediger |

## Stress extreme optionnel

```bash
python scripts/load_test.py --case text --level extreme --rate 200 --url "$URL"
python scripts/load_test.py --case text --level extreme --rate 300 --url "$URL"
python scripts/load_test.py --case text --level extreme --rate 500 --url "$URL"
```

| Rate req/min | Requetes | HTTP 200 | Succes | Latence moyenne | P95 | Restarts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer |
| 300 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer |
| 500 | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer | A mesurer |

Le point de rupture est le premier palier sous `80 %` de succes. La preuve
attendue est une sortie de `kubectl describe pod` ou `kubectl logs`, suivie
d'une capture de retour a l'etat stable deux minutes plus tard.
