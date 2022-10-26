# moNNT.py Async Usenet Server

moNNT.py is an async usenet server written in Python. To run the server, `cd` into its directory and then

```shell
$ poetry run python main.py
```

This software was written as part of my Bachelor thesis (Computer Science). It should therefore not be regarded
as a full-fledged replacement for *INN* or other production news servers. As of right now, it is a proof-of-concept
that demonstrates the operation of a news server in a disruption-tolerant network (DTN) environment. The DTN
connectivity is handled by the most excellent [dtn7-rs](https://github.com/dtn7/dtn7-rs) DTN network daemon.

For more information about how to run the server in conjunction with the `dtnd`, see the
[backend README](backend/dtn7sqlite/README.md).

## Features

- async operation for handling multiple clients simultaneously
- fully exchangeable synchronization and storage backends (see section below)
- `pyproject.toml` based configuration

## Configuration

The server is configured through the flag set in the `monntpy.env` setting in `pyproject.toml`. This controls which
configuration is loaded. In the server `config[dev|prod|test].toml` environment specific settings can be configured.

The backends must implement their own configuration scheme. For the `DTN7SQLite` backend, there is a `config.toml` in
the main backend directory.


## Exchangeable Synchronization and Storage Backends

New backends for synchronization and storage can easily be implemented by abstracting from the
`backend.base.Backend` class.

## Development Environment

Development and deployment is facilitated by the Poetry dependency manager, which also allows separate development
dependencies. Pre-commit hooks can be activated and are managed through the
[.pre-commit-config.yaml](https://github.com/teschmitt/moNNT.py/blob/main/.pre-commit-config.yaml)
configuration file. Presently, the tools [black](https://github.com/psf/black), [isort](https://github.com/PyCQA/isort)
and [flake8](https://github.com/PyCQA/flake8) are used to lint and check the source code before committing.


## Dockerized Deployment

moNNT.py can easily be run in a Docker container. As a reference setup, a
[Dockerfile](https://github.com/teschmitt/moNNT.py/blob/main/Dockerfile)
is included in this repo. It is based on the official Python 3.10.7 image
[python:3.10-slim](https://hub.docker.com/_/python) from Dockerhub.

A few notes on this: Because the current state of the main
directory is copied into the image, setup everything as you wish to encounter it
in the container. This includes settings in the `.env` files
and backend specific configurations, but also in the `Dockerfile` and
[docker/entrypoint.sh](https://github.com/teschmitt/moNNT.py/blob/main/docker/entrypoint.sh) as this will
control the execution of your server.

Then, in directory of the `Dockerfile`, run

```shell
$ docker build . --tag monntpy
```

You can then simply run the application with

```shell
$ docker run -rm -ti --network="host" monntpy
```

and connect to it on port 1190.
