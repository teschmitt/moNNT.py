# moNNT.py Async Usenet Server





## Development Environment

Development and deployment is facilitated by the Poetry dependency manager, which also allows separate development dependencies. Pre-commit hooks can be activated and are managed through the [.pre-commit-config.yaml](https://github.com/teschmitt/moNNT.py/blob/main/.pre-commit-config.yaml) configuratin file. Presently, the tools [black](https://github.com/psf/black), [isort](https://github.com/PyCQA/isort) and [flake8](https://github.com/PyCQA/flake8) are used to lint and check the source code before commiting.


## Dockerized Deployment

moNNT.py can easily be run in a Docker container. As a reference setup, a [Dockerfile](https://github.com/teschmitt/moNNT.py/blob/main/Dockerfile)
is included in this repo. It is based on the official Python 3.10.7 image [python:3.10-slim](https://hub.docker.com/_/python) from Dockerhub.

A few notes on this: Because the current state of the main
directory is copied into the image, setup everything like you want to encounter it
later on when running in the container. This includes settings in the `.env` files
and backend specific configurations, but also in the `Dockerfile` and
[docker/entrypoint.sh](https://github.com/teschmitt/moNNT.py/blob/main/docker/entrypoint.sh) as this will control the execution of your server.

Then, in directory of the `Dockerfile`, run

```shell
docker build . --tag monntpy
```

You can then simply run the application with

```shell
docker run --rm -ti -p 1190:1190 -u $(id -u):$(id -g) monntpy
```

and connect to it on port 1190.
