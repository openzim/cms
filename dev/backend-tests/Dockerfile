FROM python:3.13-slim-bookworm

# install Python dependencies first (since they change more rarely than src code)
COPY pyproject.toml README.md /app/
COPY src/cms_backend/__about__.py /app/src/cms_backend/__about__.py
RUN pip install --no-cache-dir "/app[dev]"

COPY src /app/src
COPY tests /app/tests

ENV PYTHONPATH=/app/src

WORKDIR /app/
