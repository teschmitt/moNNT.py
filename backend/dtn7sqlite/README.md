# DTN7SQLite Backend

## Getting Started

To run moNNT.py with this backend in conjunction with the `dtnd`, first start the daemon with the node ID you have
also defined in the `config.toml`, e.g. like so:

```shell
$ dtnd --nodeid n1 --cla mtcp
```

Usually, more arguments are not necessary since this backend will take care of registering all needed endpoints
through the REST and WebSocket interfaces.

Take a look in the `config.toml` to familiarize yourself with the options. All time related options are first parsed
by the [`pytimeparse2` package](https://github.com/onegreyonewhite/pytimeparse2) and can therefore be written in a
human-readable format according to the specifications of that package, e.g.

```
32m
2h32m
3d2h32m
1w3d2h32m
1w 3d 2h 32m
...
```


## Open Source Packages

For the implementation of the solution, following open source Python libraries are imported explicitly:

- [py-dtn7](https://github.com/teschmitt/py-dtn7): dtn7-rs API wrapper for Python which also offers a Bundle class (License: AGPL-3.0)

- [toml](https://github.com/uiri/toml): Python library for parsing and creating TOML (Tom's Obvious, Minimal Language) used for parsing server and backend configuration files (License: MIT)

- [Tortoise ORM](https://github.com/tortoise/tortoise-orm): Asyncio ORM (Object Relational Mapper) used to interface with the backing SQLite database (License: Apache-2.0)

- [pytimeparse2](https://github.com/onegreyonewhite/pytimeparse2): Library to parse various kinds of time expressions that can be used in configuration files (License: MIT)

- [websockets](https://github.com/aaugustin/websockets): Asyncio WebSockets library used for calls to the dtnd WS interface (License: BSD-3-Clause)
