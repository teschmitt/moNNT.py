#!/bin/bash

dtnd --nodeid "$1" --cla "$2" 2>&1 &

cd /app || exit 1
poetry run python main.py
