FROM tiangolo/uvicorn-gunicorn:python3.8-slim
LABEL org.opencontainers.image.source https://github.com/openzim/cms
ENV ALLOWED_ORIGINS http://localhost

RUN pip install --no-cache-dir --upgrade pip setuptools toml invoke

COPY pyproject.toml tasks.py /src/
RUN cd /src && invoke install-deps --package runtime && cd - && rm -rf /src

COPY src/ /app/
WORKDIR /app/
