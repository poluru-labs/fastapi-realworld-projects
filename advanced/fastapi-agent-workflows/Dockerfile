FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts/start.sh ./scripts/start.sh

RUN pip install --no-cache-dir . \
    && chmod +x ./scripts/start.sh \
    && useradd --create-home appuser

USER appuser

EXPOSE 8000

CMD ["./scripts/start.sh"]
