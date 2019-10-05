*******************************************************
Tezos Reward Distributor (Run & Forget) |Build Status|
*******************************************************

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER
CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE WITH
CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS.
IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH
THE APPLICATION. IN SERVICE MODE DO NOT UPDATE OFTEN.

What is Tezos Reward Distributor?
#################################

TRD is a software for distributing baking rewards with delegators. This
is not a script but a full scale application which can run in the
background all the time. It can track cycles and make payments. It does
not have to be used as a service, It can also be used interactively.

TRD supports complex payments, pays in batches, provides two back ends
for calculations: rpc and tzcan. It was developed and tested extensively by
the community. For more information, please check following Medium article_ and the source code which can be found in the following Github_ repo.

.. _article : https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7

.. _Github : https://github.com/habanoz/tezos-reward-distributor


How to get and install Tezos Reward Distributor?
################################################

Requirements and Setup
**********************

Python 3 is required. You can use following commands to install.

::

    sudo apt-get update
    sudo apt-get -y install python3-pip

Download the application repository using git clone:

::

    git clone https://github.com/habanoz/tezos-reward-distributor

To install required modules, use pip with requirements.txt provided.

::

    cd tezos-reward-distributor
    pip3 install -r requirements.txt

Regulary check and upgrade to the latest available version:

::

    git pull


How to configure Tezos Reward Distributor?
##########################################

Baker Configuration:
********************

Each baker has its own configuration and policy. A payment system should
be flexible enough to cover needs of bakers. The application uses a yaml
file for loading baker specific configurations.

Configuration tool can be used to create baking configuration file
interactively. Also an example configuration file is present under
examples directory. For more information on configuration details, please
see our wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/Configuration>`_.

TRD is designed to work as a linux service. It expects use of tezos
signer for encrypted payment accounts. Unencrypted payment accounts can
be used without tezos signer. If a payment account is encrypted and not
configured to be signed by tezos signer, TRD will freeze. For more
information on payment addresses please refer to our wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/Payment-Address>`_.

Email Setup
***********

Get emails for payment reports at each cycle. Fill email.ini file with
your email details to receive payment emails.

Fee Setup
*********

fee.ini file contains details about transaction fees. Currently the fee
value specified under DEFAULT domain is used as fee amount. It is in
mutez.

How to run Tezos Reward Distributor?
####################################

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
*************

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


For developers
##############

Please refer to contributions guide_ on wiki pages.

.. _guide : https://github.com/habanoz/tezos-reward-distributor/wiki/How-to-Contribute

Funding
#######

TRD is an open source project and will stay like this. It is not funded
by any organization. A grant request is rejected by Tezos Foundation.
However, I will try to continue to enhance the software and support the
community.

TRD Art Work
############

This Github Repo_ contains logo images. If you are
using TRD and want to let everybody know about it, feel free to place
them in your website.

.. |Build Status| image:: https://travis-ci.com/habanoz/tezos-reward-distributor.svg?branch=development
   :target: https://travis-ci.com/habanoz/tezos-reward-distributor
.. _Repo: https://github.com/habanoz/trd-art
