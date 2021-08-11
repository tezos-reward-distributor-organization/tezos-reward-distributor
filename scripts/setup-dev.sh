#!/bin/bash
sudo apt-get update
sudo apt-get -y install python3-pip libenchant1c2a graphviz

# Upgrade pip
python3 -m pip install --upgrade pip

# Install Python required packages
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"
cd ..
pip3 install -r requirements.txt

# Install development required packages
pip3 install -r requirements-dev.txt

# Set the Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
