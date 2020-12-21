How to run Tezos Reward Distributor?
=====================================================

Command Line Usage
------------------------

For a list of parameters, run:

::

    python3 src/main.py --help

The most common use case is to run in mainnet and start to make payments
from last released rewards or continue making payments from the cycle
last payment is done:

::

    python3 src/main.py

Make payments for a single cycle:

::

    python3 src/main.py -C 42 -M 3 

Make pending payments and stop:

::

    python3 src/main.py -M 2

Make pending payments beginning from a cycle and stop:

::

    python3 src/main.py -C 30 -M 2

Run in dry-run mode in delphinet, make payments from cycle 30 and exit:

::

    python3 src/main.py -D -N DELPHINET -C 30 -M 3

Run in dry-run mode in mainnet, make payments from cycle 30 onwards,
for calculations use data provided by tezos node rpc interface:

::

    python3 src/main.py -C 30 -P rpc
