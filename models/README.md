# Validation des modeles

Le dataset utilisé est `data/comments.csv`, le jeu Jigsaw Toxic Comment
Classification obtenu depuis Hugging Face. Le fichier contient `159 571`
commentaires annotés sur six catégories et `10.17 %` de commentaires portant
au moins une étiquette toxique.

Le script reproductible `python scripts/train_models.py` sépare les données en
apprentissage et validation selon un split stratifié 80/20, entraîne un
vectoriseur TF-IDF partagé de `80 000` termes, une régression logistique
binaire et six classifieurs One-vs-Rest.

| Modèle | Usage | Métrique de validation | Résultat |
| --- | --- | --- | ---: |
| TF-IDF + LogisticRegression | Toxic / non-toxic | ROC-AUC | 0.9727 |
| TF-IDF + LogisticRegression | Routage au seuil 0.35 | F1 | 0.6773 |
| TF-IDF + OneVsRest LogisticRegression | Six catégories au seuil 0.35 | F1 macro | 0.5063 |

L'artefact `toxicity_bundle.joblib` pèse `5 250 124` octets (`5.01 MiB`).
L'inférence du bundle complet, sans HTTP, a été mesurée localement sur
300 commentaires après chauffe : `0.397 ms` en moyenne et `0.787 ms` au P95.
Ces mesures valident le choix d'un modèle léger ; le P95 bout-en-bout doit être
complété par le challenge Minikube.
