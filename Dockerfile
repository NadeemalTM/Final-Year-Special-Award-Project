FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system teaapp \
    && adduser --system --ingroup teaapp teaapp

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=teaapp:teaapp app.py model_metadata.json ./
COPY --chown=teaapp:teaapp reasonable_price_deployment_model.joblib prediction_feature_store.csv ./
COPY --chown=teaapp:teaapp research/docs/factory_region_mapping.csv ./research/docs/factory_region_mapping.csv
RUN mkdir -p /app/research/user_evaluation \
    && chown -R teaapp:teaapp /app/research

USER teaapp
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
