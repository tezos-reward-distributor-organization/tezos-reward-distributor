Installation
============

Requirements and Setup
----------------------

Download the application repository using git clone:

::

    git clone https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor
    cd tezos-reward-distributor

Install Python 3 and pip (if not already installed) and required packages with:

::

    ./scripts/setup.sh

The Tezos signer is also needed to run TRD. Please check out the official Tezos documentation_ and install the Tezos signer.

.. _documentation : https://tezos.gitlab.io/introduction/howtoget.html

Update
------

Regulary check and upgrade to the latest available version:

::

    ./scripts/update.sh

Development
-----------

Developers and testers need to install additional packages:

::

    ./scripts/setup-dev.sh
