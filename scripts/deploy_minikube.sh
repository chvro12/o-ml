#!/usr/bin/env sh
set -eu

NAMESPACE="projet-pst"

for CMD in docker minikube kubectl; do
  if ! command -v "${CMD}" >/dev/null 2>&1; then
    printf 'Commande manquante: %s\n' "${CMD}" >&2
    exit 127
  fi
done

minikube start --cpus=4 --memory=6144 --driver=docker
minikube addons enable metrics-server
kubectl apply -f k8s/
kubectl rollout status deployment/preprocessing -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/monitoring -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/inference -n "${NAMESPACE}" --timeout=180s
kubectl get all -n "${NAMESPACE}"
kubectl describe resourcequota projet-quota -n "${NAMESPACE}"
