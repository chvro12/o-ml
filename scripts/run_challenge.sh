#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s http://HOST:PORT/predict\n' "$0" >&2
  exit 2
fi

URL="$1"
NAMESPACE="projet-pst"
PYTHON_BIN="${PYTHON:-python3}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="evidence/${STAMP}"
mkdir -p "${OUT}"

for CMD in kubectl curl "${PYTHON_BIN}"; do
  if ! command -v "${CMD}" >/dev/null 2>&1; then
    printf 'Commande manquante: %s\n' "${CMD}" >&2
    exit 127
  fi
done

kubectl get all -n "${NAMESPACE}" > "${OUT}/cluster-get-all-before.txt"
kubectl describe resourcequota projet-quota -n "${NAMESPACE}" \
  > "${OUT}/quota-before.txt"

for LEVEL in nominal charge stress; do
  printf 'Execution du niveau %s\n' "${LEVEL}"
  kubectl get pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-pods-before.txt"
  kubectl top pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-top-before.txt"
  "${PYTHON_BIN}" scripts/load_test.py --case text --level "${LEVEL}" --url "${URL}" \
    | tee "${OUT}/${LEVEL}-load-test.txt" &
  TEST_PID="$!"
  SAMPLE_PID=""
  if [ "${LEVEL}" != "nominal" ]; then
    (
      while kill -0 "${TEST_PID}" 2>/dev/null; do
        date -u
        kubectl top pods -n "${NAMESPACE}"
        sleep 30
      done
    ) > "${OUT}/${LEVEL}-top-every-30s.txt" &
    SAMPLE_PID="$!"
  fi
  wait "${TEST_PID}"
  if [ -n "${SAMPLE_PID}" ]; then
    kill "${SAMPLE_PID}" 2>/dev/null || true
  fi
  kubectl top pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-top-after.txt"
  kubectl get pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-pods-after.txt"
  kubectl port-forward svc/monitoring-svc -n "${NAMESPACE}" 18002:8002 \
    > "${OUT}/${LEVEL}-port-forward.txt" 2>&1 &
  FORWARD_PID="$!"
  trap 'kill "${FORWARD_PID}" 2>/dev/null || true' EXIT
  sleep 2
  curl --fail --silent http://127.0.0.1:18002/metrics \
    > "${OUT}/${LEVEL}-metrics.txt"
  curl --fail --silent http://127.0.0.1:18002/predictions \
    > "${OUT}/${LEVEL}-predictions.json"
  kill "${FORWARD_PID}" 2>/dev/null || true
  trap - EXIT
done

kubectl get all -n "${NAMESPACE}" > "${OUT}/cluster-get-all-after.txt"
printf 'Preuves ecrites dans %s\n' "${OUT}"
