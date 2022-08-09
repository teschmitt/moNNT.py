# moNNT.py Async Usenet Server



## Dockerized Setup

moNNT.py can easily be run in a Docker container. As a reference setup, a `Dockerfile`
is included in this repo.

A few notes on this: Because the current state of the main
directory is copied into the image, setup everything like you want to encounter it
later on when running in the container. This includes settings in the `.env` files
and backend specific configurations, but also in the `Dockerfile` and
`docker/entrypoint.sh` as this will control the execution of your server.

Then, in directory of the `Dockerfile`, run

```shell
docker build . --tag monntpy
```

You can then simply run the application with

```shell
docker run --rm -ti -p 1190:1190 -u $(id -u):$(id -g) monntpy
```

and connect to it on port 1190.
