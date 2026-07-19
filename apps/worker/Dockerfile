FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/src ./worker/src
COPY api/src ./api/src
ENV PYTHONPATH=/app/worker/src:/app/api/src
CMD ["python", "-m", "celery", "-A", "sic_worker.app:celery_app", "worker", "--beat", "--loglevel=INFO"]
