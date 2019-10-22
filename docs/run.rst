How to run Tezos Reward Distributor?
=====================================================

For a list of parameters, run:

::

    python3 src/main.py --help

The most common use case is to run in mainnet and start to make payments
from last released rewards or continue making payments from the cycle
last payment is done.

::

    python3 src/main.py

For more example commands please see wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/How-to-Run>`_.


Linux Service
------------------------

Alternatively, it is possible to add tezos-reward-distributer as a Linux service. It
can run in the background.

If docker is used, make sure user is in docker group

::

    sudo usermod -a -G docker $USER

In order to set up the service with default configuration arguments, run
the following command:

::

    sudo python3 service_add.py

For more information please refer to this wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/Linux-Service>`_.



