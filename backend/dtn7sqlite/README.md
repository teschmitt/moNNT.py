# DTN7-SQLite Backend


## Open Source Packages

For the implementation of the solution, following open source Python libraries are imported explicitly:

- [py-dtn7](https://github.com/teschmitt/py-dtn7): dtn7-rs API wrapper for Python which also offers a Bundle class (License: AGPL-3.0)

- [toml](https://github.com/uiri/toml): Python library for parsing and creating TOML (Tom's Obvious, Minimal Language) used for parsing server and backend configuration files (License: MIT)

- [Tortoise ORM](https://github.com/tortoise/tortoise-orm): Asyncio ORM (Object Relational Mapper) used to interface with the backing SQLite database (License: Apache-2.0)

- [pytimeparse2](https://github.com/onegreyonewhite/pytimeparse2): Library to parse various kinds of time expressions that can be used in configuration files (License: MIT)

- [websockets](https://github.com/aaugustin/websockets): Asyncio WebSockets library used for calls to the dtnd WS interface (License: BSD-3-Clause)
