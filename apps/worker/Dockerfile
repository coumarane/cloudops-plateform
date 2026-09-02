FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api:/app/worker

COPY apps/api/requirements.txt /tmp/api-requirements.txt
COPY apps/worker/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/api-requirements.txt -r /tmp/worker-requirements.txt

COPY apps/api/ /app/api/
COPY apps/worker/ /app/worker/

WORKDIR /app/worker

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
