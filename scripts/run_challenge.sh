#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s http://HOST:PORT/predict\n' "$0" >&2
  exit 2
fi

URL="$1"
NAMESPACE="projet-pst"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="evidence/${STAMP}"
mkdir -p "${OUT}"

for LEVEL in nominal charge stress; do
  printf 'Execution du niveau %s\n' "${LEVEL}"
  kubectl get pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-pods-before.txt"
  kubectl top pods -n "${NAMESPACE}" > "${OUT}/${LEVEL}-top-before.txt"
  python scripts/load_test.py --case text --level "${LEVEL}" --url "${URL}" \
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
  sleep 2
  curl --fail --silent http://127.0.0.1:18002/metrics \
    > "${OUT}/${LEVEL}-metrics.txt"
  curl --fail --silent http://127.0.0.1:18002/predictions \
    > "${OUT}/${LEVEL}-predictions.json"
  kill "${FORWARD_PID}" 2>/dev/null || true
done

printf 'Preuves ecrites dans %s\n' "${OUT}"
