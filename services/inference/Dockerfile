FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/models/toxicity_bundle.joblib
WORKDIR /opt/service

COPY services/inference/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 appuser

COPY services/inference/app ./app
COPY models /models
RUN chown -R appuser:appuser /models
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "30", "app.main:app"]
