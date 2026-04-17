FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY rcm_mc/ rcm_mc/
COPY configs/ configs/

RUN pip install --no-cache-dir -e ".[all]"

ENTRYPOINT ["rcm-mc"]
CMD ["--help"]
