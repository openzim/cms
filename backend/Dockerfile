FROM python:3.13-slim-bookworm
LABEL org.opencontainers.image.source https://github.com/openzim/cms

ENV INIT_PASSWORD admin

# curl needed for healthcheck
RUN apt-get update && apt-get install -y curl supervisor && \
    rm -rf /var/lib/apt/lists/*

# prestart script (former entrypoint - database init)
COPY prestart.sh /app/prestart.sh
RUN chmod +x /app/prestart.sh

# install Python dependencies first (since they change more rarely than src code)
COPY pyproject.toml README.md /app/
COPY src/cms_backend/__about__.py /app/src/cms_backend/__about__.py
RUN pip install --no-cache-dir /app

COPY src /app/src

RUN pip install --no-cache-dir /app  \
    && rm -rf /app/src \
    && rm /app/pyproject.toml \
    && rm /app/README.md

EXPOSE 80

COPY periodic.conf /etc/supervisor/conf.d/periodic.conf

CMD ["/usr/bin/supervisord", "-n", "-u", "root"]
