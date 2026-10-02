FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 SOURCE_DATE_EPOCH=1760000000
WORKDIR /build
COPY requirements-build.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-build.lock
COPY pyproject.toml ./
COPY app ./app
COPY scripts ./scripts
RUN python -m build --wheel --no-isolation --outdir /wheels

FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production DATA_DIR=/var/lib/waaxalma \
    STATIC_DIR=/var/lib/waaxalma/static UPLOAD_DIR=/var/lib/waaxalma/uploads \
    HOME=/tmp
WORKDIR /opt/waaxalma
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-deps /wheels/*.whl \
    && rm -rf /wheels \
    && groupadd --gid 10001 waaxalma \
    && useradd --uid 10001 --gid 10001 --no-create-home waaxalma \
    && mkdir -p /var/lib/waaxalma/static/audio /var/lib/waaxalma/uploads \
    && chown -R 10001:10001 /var/lib/waaxalma
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"
CMD ["waaxalma-backend"]
