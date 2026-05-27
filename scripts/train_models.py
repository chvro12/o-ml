#!/usr/bin/env python3
"""Entraine les modeles TF-IDF du cas de moderation textuelle."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "comments.csv"
MODEL_PATH = ROOT / "models" / "toxicity_bundle.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
RANDOM_STATE = 42
CATEGORIES = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]


def train() -> dict[str, float | int]:
    frame = pd.read_csv(DATA_PATH)
    texts = frame["comment_text"].fillna("").astype(str)
    targets = frame[CATEGORIES].astype(int)
    binary = (targets.sum(axis=1) > 0).astype(int)
    x_train, x_test, y_train, y_test, cat_train, cat_test = train_test_split(
        texts,
        binary,
        targets,
        test_size=0.2,
        stratify=binary,
        random_state=RANDOM_STATE,
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        max_features=80000,
        min_df=2,
        sublinear_tf=True,
        dtype=np.float32,
    )
    train_matrix = vectorizer.fit_transform(x_train)
    test_matrix = vectorizer.transform(x_test)

    binary_model = LogisticRegression(
        max_iter=300, class_weight="balanced", solver="liblinear", random_state=RANDOM_STATE
    )
    binary_model.fit(train_matrix, y_train)
    binary_score = binary_model.predict_proba(test_matrix)[:, 1]
    binary_prediction = (binary_score >= 0.35).astype(int)

    category_model = OneVsRestClassifier(
        LogisticRegression(
            max_iter=300,
            class_weight="balanced",
            solver="liblinear",
            random_state=RANDOM_STATE,
        )
    )
    category_model.fit(train_matrix, cat_train)
    category_score = category_model.predict_proba(test_matrix)
    category_prediction = (category_score >= 0.35).astype(int)

    bundle = {
        "vectorizer": vectorizer,
        "binary_model": binary_model,
        "category_model": category_model,
        "categories": CATEGORIES,
        "toxic_threshold": 0.35,
        "category_threshold": 0.35,
    }
    joblib.dump(bundle, MODEL_PATH, compress=3)
    metrics = {
        "dataset_rows": int(len(frame)),
        "toxic_rate_pct": round(float(binary.mean() * 100), 2),
        "binary_roc_auc": round(float(roc_auc_score(y_test, binary_score)), 4),
        "binary_f1_threshold_035": round(float(f1_score(y_test, binary_prediction)), 4),
        "categories_macro_f1_threshold_035": round(
            float(f1_score(cat_test, category_prediction, average="macro", zero_division=0)), 4
        ),
        "artifact_bytes": int(MODEL_PATH.stat().st_size),
        "vocabulary_size": int(len(vectorizer.vocabulary_)),
        "random_state": RANDOM_STATE,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
