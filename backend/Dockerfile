FROM python:3.12-slim

RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall pyasn1>=0.6.3 && \
    rm -rf /root/.cache/pip

COPY . .
ENV HF_HOME=/app/hf_cache
RUN mkdir -p /app/hf_cache && \
    find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

RUN useradd -m -u 1001 app && \
    mkdir -p /app/uploads /app/hf_cache && \
    chown -R app:app /app/uploads /app/hf_cache && \
    chmod 755 /app/uploads /app/hf_cache

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
