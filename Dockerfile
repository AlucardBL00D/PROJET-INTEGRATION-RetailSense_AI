FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RETAILSENSE_MODELS_DIR=/app/models \
    RETAILSENSE_MODEL_REGISTRY_PATH=/app/models/model_registry.json

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY api /app/api
COPY models /app/models
COPY .env.example /app/.env.example

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
