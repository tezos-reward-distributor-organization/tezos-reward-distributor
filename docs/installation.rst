How to get and install TRD?
=====================================================

Requirements and Setup
------------------------


Python 3
-----------

Mac: 

::

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    brew install python3

Linux:

::

    sudo apt-get update
    sudo apt-get -y install python3-pip

Tezos
-----------

Mac: 

::

    brew install hidapi libev wget

Mac & Linux:

Follow instructions found here: https://tezos.gitlab.io/introduction/howtoget.html

TRD
-----------

::
    
    git clone https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor

To install required modules, use pip with requirements.txt provided.

::

    pip3 install -r requirements.txt

Regulary check and upgrade to the latest available version:

::

    git pull
