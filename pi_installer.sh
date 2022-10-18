#!/bin/bash

cur=$(pwd)

# Upgrade system and install needed packages for poetry and git
sudo apt update
sudo apt -y upgrade
sudo apt install -y git python3-poetry

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Install dtn7-rs
cargo install --bins --examples dtn7

# Install moNNT.py into ~/moNNT.py
git clone https://github.com/teschmitt/moNNT.py.git
cd moNNT.py
poetry install --no-dev

cd "$cur"

# Now you can start dtnd, then cd into moNNT.py and run:
# poetry run python main.py
