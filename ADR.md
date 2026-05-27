# ADR - Moderation textuelle sous quota Kubernetes

## Decision et contexte

Le cas choisi est le cas 2, moderation de commentaires textuels, soumis a un
quota de `3000m` CPU et `2Gi` de memoire ainsi qu'a une latence attendue sous
`500 ms`. La decision centrale est de retenir TF-IDF avec regression logistique
plutot que DistilBERT. DistilBERT apporterait une meilleure comprehension
contextuelle, mais deux modeles ou plusieurs workers approcheraient rapidement
la limite memoire du cas. TF-IDF est suffisamment compact pour reserver une
marge de deploiement et supporter le stress test.

Le dataset est Jigsaw Toxic Comment Classification, telecharge depuis le depot
Hugging Face `thesofakillers/jigsaw-toxic-comment-classification-challenge`,
source sans compte indiquee pour le cas 2 et distribuee sous licence CC0 selon
le sujet. Le fichier `data/comments.csv` contient les commentaires et les six
labels `toxic`, `severe_toxic`, `obscene`, `threat`, `insult` et
`identity_hate`. L'entrainement exploite l'ensemble disponible, avec un split
stratifie 80/20 pour la validation.

## Architecture retenue

Le script de charge impose de contacter un Service nomme `inference-svc` avec
`POST /predict`. Cet alias externe cible le pod de preprocessing, car le
preprocessing doit recevoir les donnees brutes : il normalise les espaces et
limite la taille du commentaire, puis transmet le texte prepare par REST au
service interne `model-svc`. Celui-ci porte l'inference principale, vectorise
le texte et calcule un score binaire. Lorsque le score depasse `0.35`, le
second modele produit les categories fines pertinentes. La reponse conserve le
contrat impose `{"label": str, "score": float}` et ajoute `categories`.

Apres la reponse de l'inference, le preprocessing publie vers `monitoring-svc`
le statut, la latence bout-en-bout et la prediction. Le monitoring conserve les
100 dernieres predictions et expose les indicateurs de volume, erreurs et
latence sur `/metrics`, ainsi que `/predictions` pour la demonstration. Tous
les appels internes utilisent les noms DNS Kubernetes et non des IP de pods.

## Modeles et ressources

Un unique vectoriseur TF-IDF est partage par les deux modeles afin d'eviter de
dupliquer le vocabulaire en memoire. Le premier classifieur est une regression
logistique binaire. Le second est un ensemble One-vs-Rest de six regressions
logistiques, correspondant a la nature multi-label du dataset. Les deux
services HTTP utilisent deux workers Gunicorn pour absorber les appels
concurrents ; le monitoring reste a un worker afin de ne pas fragmenter son
historique en memoire.

| Service actif | Requests CPU | Requests memoire | Limits CPU | Limits memoire |
| --- | ---: | ---: | ---: | ---: |
| Preprocessing et entree publique | 200m | 128Mi | 500m | 192Mi |
| Inference TF-IDF | 800m | 512Mi | 1500m | 1024Mi |
| Monitoring | 100m | 96Mi | 200m | 160Mi |
| Total nominal | **1100m** | **736Mi** | **2200m** | **1376Mi** |
| Quota cas 2 | **3000m** | **2048Mi** | **3000m** | **2048Mi** |
| Marge nominale | **1900m** | **1312Mi** | **800m** | **672Mi** |

Les valeurs sont des allocations initiales fondees sur la taille du modele et
doivent etre confrontees a `kubectl top pods` pendant le challenge. Un
RollingUpdate de l'inference avec un pod supplementaire consommerait en limits
`3700m / 2400Mi`, au-dessus du quota. L'inference utilise donc `Recreate`. Le
preprocessing peut utiliser `RollingUpdate` car sa pointe atteint
`2700m / 1568Mi`, et le monitoring aussi car sa pointe atteint
`2400m / 1536Mi`, toutes deux sous le quota.

## Livraison

GitHub Actions est retenu pour deux raisons concretes : la validation s'execute
directement au push du depot remis, et les identifiants Docker Hub restent dans
les secrets GitHub. Le job de tests reentraine les modeles et impose une
couverture de `80 %`. Le job d'images ne peut s'executer qu'apres son succes ;
il construit toujours les trois images et les pousse lorsque les secrets Docker
Hub sont configures.

Le script `scripts/deploy_minikube.sh` construit les images depuis un clone,
applique tous les manifests sous `k8s/` et attend les trois deployments. Il
evite toute intervention manuelle ou dependance a un etat Docker preexistant
sur la machine de demonstration.
