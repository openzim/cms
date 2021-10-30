FROM tiangolo/uvicorn-gunicorn:python3.8-slim
LABEL org.opencontainers.image.source https://github.com/openzim/cms

# to set to your clients' origins
ENV ALLOWED_ORIGINS http://localhost

# internal
ENV APP_MODULE "backend.main:app"

RUN rm -f /app/main.py  # from upstream image
WORKDIR /src
RUN pip install --no-cache-dir --upgrade pip setuptools toml invoke
COPY pyproject.toml README.md setup.cfg setup.py tasks.py /src/
RUN invoke install-deps --package runtime
COPY src/ /src/src
RUN python setup.py install
WORKDIR /app/
