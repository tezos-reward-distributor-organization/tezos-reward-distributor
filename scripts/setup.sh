#!/bin/bash
sudo apt-get update
sudo apt-get -y install python3-pip

# Upgrade pip
python3 -m pip install --upgrade pip

# Install Python required packages
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"
pip3 install -r ../requirements.txt
