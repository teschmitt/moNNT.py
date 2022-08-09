#!/bin/bash

# This setup relies on the dtn7sqlite backend but can be adapted
# to any other configuration. For this setup, we first need to
# start the DTN daemon, then out moNNT.py server
dtnd --nodeid n1 --cla mtcp 2>&1 &

cd /app || exit 1
python main.py
