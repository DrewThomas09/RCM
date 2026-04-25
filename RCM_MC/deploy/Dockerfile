FROM python:3.14-slim

LABEL maintainer="RCM-MC Team"
LABEL description="RCM-MC analytics platform"

WORKDIR /app

# Install system deps for numpy/pandas builds
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY rcm_mc/ rcm_mc/

RUN pip install --no-cache-dir .

# Default data directory for SQLite persistence
RUN mkdir -p /data
ENV RCM_MC_DB=/data/rcm_mc.db

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["python", "-m", "rcm_mc", "serve"]
# --host 0.0.0.0 is REQUIRED. rcm-mc serve's default is 127.0.0.1,
# which only works for processes inside the container — the Docker
# port forward (`-p 8080:8080`) and any reverse-proxy sidecar (Caddy
# et al.) need the server to bind to 0.0.0.0. The in-container
# HEALTHCHECK above silently passes either way, so this is the
# subtle misconfiguration that makes "why is it unreachable?" hard
# to debug without looking at netstat.
CMD ["--db", "/data/rcm_mc.db", "--port", "8080", "--host", "0.0.0.0"]
