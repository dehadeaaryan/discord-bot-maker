FROM python:3.15.0-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements-server.lock ./
RUN pip install --no-cache-dir -r requirements-server.lock
COPY pyproject.toml setup.py README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps . && useradd --uid 10001 --create-home app
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY apps/runner ./apps/runner
COPY migrations ./migrations
COPY alembic.ini ./
USER app
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "64", "--backlog", "128", "--timeout-keep-alive", "5"]
