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

L'artefact commun aux deux predictions mesure `5.01 MiB`. Les deux workers de
l'inference en chargent chacun une copie, soit environ `10 MiB` de poids et de
vocabulaire serialises, avant les structures Python, scikit-learn et les
matrices crees pendant les appels concurrents. La reservation `512Mi` et la
limite `1024Mi` laissent donc une marge volontaire pour l'execution et les
pointes de requetes. Le preprocessing ne charge pas de modele et ne conserve
pas de corpus ; `128Mi / 192Mi` couvrent ses deux workers et les appels HTTP.
Le monitoring ne conserve que des compteurs et les 100 dernieres predictions ;
`96Mi / 160Mi` sont alloues a son worker unique. Ces estimations doivent etre
confirmees par `kubectl top pods` lors de l'execution Kubernetes.

| Service actif | Requests CPU | Requests memoire | Limits CPU | Limits memoire |
| --- | ---: | ---: | ---: | ---: |
| Preprocessing et entree publique | 200m | 128Mi | 500m | 192Mi |
| Inference TF-IDF | 800m | 512Mi | 1500m | 1024Mi |
| Monitoring | 100m | 96Mi | 200m | 160Mi |
| Total nominal | **1100m** | **736Mi** | **2200m** | **1376Mi** |
| Quota cas 2 | **3000m** | **2048Mi** | **3000m** | **2048Mi** |
| Marge nominale | **1900m** | **1312Mi** | **800m** | **672Mi** |

Les requests nominales sont `1100m / 736Mi`, sous le quota `3000m / 2048Mi`.
Lors d'un surge d'un pod, le preprocessing atteindrait en requests
`1300m / 864Mi`, et le monitoring `1200m / 832Mi`, toujours sous le quota.
Leurs pointes en limits restent egalement admissibles, respectivement
`2700m / 1568Mi` et `2400m / 1536Mi` : ils utilisent `RollingUpdate`.
En revanche, un pod d'inference supplementaire atteindrait, en limits,
`3700m / 2400Mi`, au-dessus du quota, meme si ses requests (`1900m / 1248Mi`)
resteraient admissibles. L'inference utilise donc `Recreate`.

## Livraison

GitHub Actions est retenu pour deux raisons concretes : la validation s'execute
directement au push du depot remis, et les identifiants Docker Hub restent dans
les secrets GitHub. Le job de tests reentraine les modeles et impose une
couverture de `80 %`. Le job d'images ne peut s'executer qu'apres son succes ;
il construit toujours les trois images et les pousse lorsque les secrets Docker
Hub sont configures.

Le script `scripts/deploy_minikube.sh` demarre Minikube, tire les images
versionnees depuis Docker Hub, applique tous les manifests sous `k8s/` et
attend les trois deployments. Il evite toute intervention manuelle et ne depend
pas d'un build Docker local avant la demonstration.
