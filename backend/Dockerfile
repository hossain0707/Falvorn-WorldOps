FROM python:3.12-slim AS build
WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip wheel --no-cache-dir --wheel-dir /wheels .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN useradd --create-home --uid 10001 worldops
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --chown=worldops:worldops frontend /srv/frontend
COPY --chown=worldops:worldops backend/alembic.ini /srv/alembic.ini
COPY --chown=worldops:worldops backend/alembic /srv/alembic
ENV FRONTEND_DIR=/srv/frontend
USER worldops
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
