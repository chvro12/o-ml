# Déploiement

Ce dépôt implémente le cas 2 : modération de contenu textuel Jigsaw avec une
latence cible inférieure à `500 ms`. Le système utilise un modèle binaire de
toxicité et un classifieur fin parmi les six catégories annotées. Le namespace
Kubernetes est `projet-pst`.

## Kubernetes depuis un clone

Prérequis : Docker, Minikube et `kubectl` accessibles depuis le terminal.

```bash
git clone https://github.com/chvro12/o-ml.git tp-text
cd tp-text
./scripts/deploy_minikube.sh
```

Cette commande démarre Minikube, tire les trois images versionnées depuis
Docker Hub, applique l'ensemble des manifests et attend les déploiements.
L'URL publique porte le nom attendu par le script de charge et dirige les
commentaires bruts vers le preprocessing, qui les transmet ensuite au modèle
interne :

```bash
kubectl get all -n projet-pst
kubectl describe resourcequota projet-quota -n projet-pst
URL="$(minikube service inference-svc -n projet-pst --url)/predict"
printf '%s\n' "$URL"
```

## Challenge de charge

```bash
python3 -m venv .venv-load
. .venv-load/bin/activate
pip install requests==2.32.3
python scripts/load_test.py --case text --level nominal --url "$URL"
python scripts/load_test.py --case text --level charge --url "$URL"
python scripts/load_test.py --case text --level stress --url "$URL"
```

Le protocole complet avec archivage des résultats, métriques et prédictions :

```bash
./scripts/run_challenge.sh "$URL"
```

Consultation en direct du monitoring :

```bash
kubectl port-forward svc/monitoring-svc -n projet-pst 8002:8002
curl http://127.0.0.1:8002/metrics
curl http://127.0.0.1:8002/predictions
kubectl top pods -n projet-pst
```

Les résultats observés doivent être consignés dans [STRESS_TEST.md](STRESS_TEST.md).

## Exécution locale avec Compose

```bash
docker compose up --build -d
open http://127.0.0.1:8000
curl -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"You are a hateful and disgusting idiot."}'
curl http://127.0.0.1:8002/metrics
curl http://127.0.0.1:8002/predictions
docker compose down
```

## Modèles

Le dataset versionné est `data/comments.csv`, issu du jeu Jigsaw Toxic Comment
Classification. `models/toxicity_bundle.joblib` regroupe :

- un vectoriseur TF-IDF partagé ;
- une régression logistique binaire `toxic` / `non-toxic` ;
- six régressions logistiques One-vs-Rest pour `toxic`, `severe_toxic`,
  `obscene`, `threat`, `insult` et `identity_hate`.

Les métriques mesurées sont détaillées dans [models/README.md](models/README.md).
Pour reproduire les artefacts et les tests :

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/train_models.py
pytest --cov=services --cov-report=term-missing --cov-fail-under=80
```

## Architecture

Le service exposé publiquement sous le nom `inference-svc` est l'entrée du
pipeline : il reçoit `{"text": "..."}`, normalise le texte dans le pod de
preprocessing puis appelle le service interne `model-svc`. L'inférence calcule
le score binaire ; lorsque le score dépasse `0.35`, elle appelle le second
modèle et renvoie les catégories fines. Le preprocessing publie la latence,
le statut HTTP et la prédiction auprès de `monitoring-svc`.

| Composant | Port | Rôle |
| --- | ---: | --- |
| `inference-svc` / preprocessing | 8000 | Entrée publique, préparation et télémétrie |
| `model-svc` / inference | 8000 | TF-IDF, toxicité et catégories fines |
| `monitoring-svc` | 8002 | Requêtes, prédictions, latence et erreurs |

Les images Kubernetes utilisées sont :

- `sambathiam/tp-text-preprocessing:1.0.0`
- `sambathiam/tp-text-monitoring:1.0.0`
- `sambathiam/tp-text-inference:1.0.0`

Les choix techniques et les calculs de ressources sont justifiés dans
[ADR.md](ADR.md).

## CI/CD

Le workflow GitHub Actions [ci.yml](.github/workflows/ci.yml) réentraîne les
artefacts, impose `80 %` de couverture puis construit les images uniquement si
les tests réussissent. Si `DOCKERHUB_USERNAME` et `DOCKERHUB_TOKEN` sont
configurés dans les secrets GitHub, les images sont publiées sur Docker Hub
avec le tag `1.0.0`.
