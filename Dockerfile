FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# setuptools must be installed first, directly in this stage
RUN pip install --no-cache-dir setuptools==69.5.1

COPY requirements-serving.txt .
RUN pip install --no-cache-dir -r requirements-serving.txt

COPY src/serving/app.py src/serving/app.py
COPY src/serving/__init__.py src/serving/__init__.py

RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

ENV MODEL_NAME="geosentinel-anomaly-detector"
ENV MODEL_STAGE="Staging"
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["sh", "-c", "uvicorn src.serving.app:app --host 0.0.0.0 --port $PORT"]
