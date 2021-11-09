FROM tiangolo/uvicorn-gunicorn:python3.8-slim
LABEL org.opencontainers.image.source https://github.com/openzim/cms

# to set to your clients' origins
ENV ALLOWED_ORIGINS http://localhost
ENV DATABASE_URL sqlite:///local.db

# internal
ENV APP_MODULE "backend.main:app"

# launched by upstream /start.sh
COPY prestart.sh /app/prestart.sh
RUN chmod +x /app/prestart.sh

# reove from upstream image
RUN rm -f /app/main.py

WORKDIR /tmp
RUN pip install --no-cache-dir --upgrade pip setuptools toml invoke
COPY pyproject.toml README.md setup.cfg setup.py tasks.py /tmp/
RUN invoke install-deps --package runtime
COPY src/ /tmp/src
RUN python setup.py install && mv /tmp/src /src
WORKDIR /src

# from upsteam
CMD ["/start.sh"]
