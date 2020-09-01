How to get and install Tezos Reward Distributor?
=====================================================

Requirements and Setup
------------------------


Python 3 is required. You can use following commands to install.

::

    sudo apt-get update
    sudo apt-get -y install python3-pip

Download the application repository using git clone:

::

    git clone https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor

To install required modules, use pip with requirements.txt provided.

::

    cd tezos-reward-distributor
    pip3 install -r requirements.txt

Regulary check and upgrade to the latest available version:

::

    git pull
