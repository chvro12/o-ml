#!/usr/bin/env sh
set -eu

NAMESPACE="projet-pst"
VERSION="1.0.0"

minikube start --cpus=4 --memory=6144 --driver=docker
minikube addons enable metrics-server
minikube image build -t "tp-text-preprocessing:${VERSION}" -f services/preprocessing/Dockerfile .
minikube image build -t "tp-text-monitoring:${VERSION}" -f services/monitoring/Dockerfile .
minikube image build -t "tp-text-inference:${VERSION}" -f services/inference/Dockerfile .
kubectl apply -f k8s/
kubectl rollout status deployment/preprocessing -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/monitoring -n "${NAMESPACE}" --timeout=180s
kubectl rollout status deployment/inference -n "${NAMESPACE}" --timeout=180s
kubectl get all -n "${NAMESPACE}"
