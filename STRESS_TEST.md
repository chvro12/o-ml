# Challenge de charge - moderation textuelle

## Protocole

```bash
kubectl port-forward svc/inference-svc -n projet-pst 18080:8000
URL="http://127.0.0.1:18080/predict"
./scripts/run_challenge.sh "$URL"
```

Sur macOS avec le driver Docker de Minikube, le tunnel `minikube service --url`
reste attache au terminal. Le `port-forward` Kubernetes a donc ete utilise pour
obtenir une URL stable pendant les mesures.

Pendant `charge` et `stress`, `scripts/run_challenge.sh "$URL"` enregistre les
sorties de charge, les metriques du monitoring, les predictions et
`kubectl top pods` toutes les 30 secondes dans un dossier date
`evidence/YYYYMMDD-HHMMSS/`.

## Mesures obligatoires

| Niveau | Rate req/min | Requetes | HTTP 200 | Succes | Latence moyenne | P95 | Restarts | Preuve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Nominal | 10 | 50 | 50 | 100.0 % | 0.059 s | 0.082 s | 0 | `evidence/20260529-134912/nominal-*` |
| Charge | 50 | 250 | 250 | 100.0 % | 0.051 s | 0.078 s | 0 | `evidence/20260529-134912/charge-*` |
| Stress | 150 | 744 | 744 | 100.0 % | 0.042 s | 0.061 s | 0 | `evidence/20260529-134912/stress-*` |

Etat du quota pendant le test :

```text
limits.cpu       2200m   / 3
limits.memory    1376Mi  / 2Gi
requests.cpu     1100m   / 3
requests.memory  736Mi   / 2Gi
```

Consommation observee en fin de stress :

| Service | CPU | Memoire |
| --- | ---: | ---: |
| inference | 14m | 253Mi |
| monitoring | 6m | 45Mi |
| preprocessing | 51m | 131Mi |

## Correction avant et apres

Le critere metier specifique au cas texte est un P95 inferieur a `500 ms`. La
correction doit etre choisie a partir du premier niveau qui depasse ce seuil ou
montre une saturation CPU. Si `model-svc` est proche de `1500m`, la premiere
hypothese a mesurer est le nombre de workers ou la taille du vocabulaire TF-IDF.

| Test relance | Configuration avant | P95 avant | Configuration apres | P95 apres | Succes apres | Conclusion |
| --- | --- | ---: | --- | ---: | ---: | --- |
| Non applicable | Deploiement Kubernetes initial sous quota cas 2 | 0.061 s | Aucune correction corrective | 0.061 s | 100.0 % | Aucun niveau problematique observe : le stress reste sous 500 ms, sans erreur ni restart. |

Conclusion : aucune correction corrective n'a ete appliquee apres les mesures,
car le systeme respecte deja la contrainte metier du cas 2 au niveau stress
impose. La decision la plus importante pour tenir le quota a ete faite en amont :
garder un modele TF-IDF + regression logistique, plus leger qu'un modele type
DistilBERT.

## Stress extreme optionnel

```bash
python scripts/load_test.py --case text --level extreme --rate 200 --url "$URL"
python scripts/load_test.py --case text --level extreme --rate 300 --url "$URL"
python scripts/load_test.py --case text --level extreme --rate 500 --url "$URL"
```

| Rate req/min | Requetes | HTTP 200 | Succes | Latence moyenne | P95 | Restarts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | Non lance | Non lance | Non lance | Non lance | Non lance | Non lance |
| 300 | Non lance | Non lance | Non lance | Non lance | Non lance | Non lance |
| 500 | Non lance | Non lance | Non lance | Non lance | Non lance | Non lance |

Le point de rupture est le premier palier sous `80 %` de succes. La preuve
attendue est une sortie de `kubectl describe pod` ou `kubectl logs`, suivie
d'une capture de retour a l'etat stable deux minutes plus tard.
