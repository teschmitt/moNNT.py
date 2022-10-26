FROM python:3.10-slim

COPY docker/entrypoint.sh /usr/local/bin
COPY . /app
WORKDIR /app

RUN pip install poetry==1.1.13 && \
  poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-root --no-dev

EXPOSE 1190

ENTRYPOINT "entrypoint.sh"
