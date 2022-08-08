FROM python:3.10-slim

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.1.13

RUN mkdir -p /app
WORKDIR /app
RUN git clone https://github.com/teschmitt/moNNT.py.git && \
    cd moNNT.py && \
    poetry install --no-interaction --no-ansi --no-root --no-dev

EXPOSE 1190

WORKDIR /app/moNNT.py
ENTRYPOINT "poetry run python main.py"
