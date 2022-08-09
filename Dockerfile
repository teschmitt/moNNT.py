FROM rust:1.58 as builder
WORKDIR /root
#RUN rustup component add rustfmt

RUN cargo install --locked --bins --examples --root /usr/local --git https://github.com/dtn7/dtn7-rs --rev 077d9a5 dtn7

FROM python:3.10-slim

COPY --from=builder /usr/local/bin/* /usr/local/bin/
COPY docker/entrypoint.sh /usr/local/bin

RUN pip install poetry==1.1.13

RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN poetry install --no-interaction --no-ansi --no-root --no-dev



EXPOSE 1190

ENTRYPOINT ["entrypoint.sh", "florentin", "mtcp"]
