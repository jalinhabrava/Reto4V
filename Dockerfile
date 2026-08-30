# syntax=docker/dockerfile:1.7

# The first stage is the only stage that needs the npm registry.  The
# resulting image contains only the compiled, local assets; the runtime never
# downloads frontend dependencies.
FROM node:22-bookworm-slim AS frontend-build

WORKDIR /src
COPY package*.json ./
RUN if [ -f package-lock.json ]; then \
      npm ci --ignore-scripts; \
    else \
      npm install --ignore-scripts; \
    fi
COPY frontend ./frontend

# The package script owns the Vite config path.  The fallback keeps this image
# compatible with a future manifest that moves the config to the repository
# root without adding a second --config argument to the current script.
RUN if grep -q 'frontend/vite.config.js' package.json; then \
      npm run build; \
    elif [ -f frontend/vite.config.js ]; then \
      npm run build -- --config frontend/vite.config.js; \
    else \
      npm run build; \
    fi


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Keep the runtime image small and non-root.  The committed requirements.lock
# is exported from uv.lock and contains hashes for every production package.
# Installing from that file makes the image reproducible and avoids resolving
# a different dependency graph during a classroom deployment.
RUN groupadd --system --gid 10001 reto4v \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /usr/sbin/nologin reto4v \
    && apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./
COPY . .

# The lock file includes gunicorn and the static Bash parser used by the
# evaluator.  Keep --require-hashes enabled: an accidental unpinned package
# must fail the build instead of silently changing the runtime image.
RUN python -m pip install --no-cache-dir --require-hashes \
      --disable-pip-version-check --no-input -r requirements.lock \
    && python -m pip check

# Vite writes the compiled files to static/dist.  Copy after the source tree
# so a .dockerignore entry can keep generated assets out of the build context.
COPY --from=frontend-build /src/static/dist ./static/dist

COPY scripts/container-entrypoint.sh /usr/local/bin/reto4v-entrypoint
RUN chmod 0755 /usr/local/bin/reto4v-entrypoint \
    && mkdir -p /app/staticfiles /app/media /app/data \
    && chown -R reto4v:reto4v /app

USER reto4v

EXPOSE 8000

# The dedicated endpoint checks that Django can reach its configured database.
# Keep HEALTHCHECK_PATH configurable for a centre-managed proxy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:8000'+os.environ.get('HEALTHCHECK_PATH','/health/'), timeout=3)"

ENTRYPOINT ["/usr/local/bin/reto4v-entrypoint"]
CMD ["gunicorn", "aulaweb.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "--graceful-timeout", "30"]
