Tezos Reward Distributor (Run & Forget) |Build Status|
======================================================

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS.
IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL
TESTED, PLEASE USE IT WITH CARE. ALWAYS MAKE A PRE-RUN IN
DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO
RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH
THE APPLICATION. IN SERVICE MODE ONLY UPDATE IF NEEDED.

What is Tezos Reward Distributor?
------------------------------------------------

TRD is a software for distributing staking rewards of
delegators introduced in detail in this Medium article_.
This is not a script but a full scale application which
can continuously run in the background as a Linux service.
It can track cycles and make payments. However it does
not have to be used as a service, but it can also be
used interactively.

TRD supports complex payments, pays in batches, provides
two back ends for calculations: rpc and tzstats_.
Developed and tested extensively by the community and the
source code which can be found in the following Github_ repo.

**Important note:**

The terms_ of tzstats note that a license is needed for
the commercial use of the API!

> If you wish to use the Data in a manner that is primarily
> intended for or directed towards commercial advantage or
> monetary compensation (such use, “Commercial Use”),
> KIDTSUNAMI requires that you enter into a separate
> commercial license agreement. Entering into a separate
> commercial license allows us to protect KIDTSUNAMI’s
> investment in the Data and to maintain the integrity of
>the Data.
>
> Please contact us at license@kidtsunami.com for more
> information about Commercial Uses of our Data.

.. _article : https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7

.. _tzstats : https://tzstats.com/

.. _terms : https://tzstats.com/terms

.. _Github : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor

.. toctree::
   :maxdepth: 2
   :caption: Tezos Reward Distributor:

   installation
   configuration
   paymentaddress
   tezossigner
   tezossignerdocker
   run
   linuxservice
   contributers

Funding
------------------------

TRD is an open source project and will stay like this. It is not funded
by any organization. A grant request is rejected by Tezos Foundation.
However, I will try to continue to enhance the software and support the
community.

TRD Art Work
------------------------

This Github Repo_ contains logo images. If you are
using TRD and want to let everybody know about it, feel free to place
them in your website.

.. |Build Status| image:: https://travis-ci.com/tezos-reward-distributor-organization/tezos-reward-distributor.svg?branch=master
   :target: https://travis-ci.com/tezos-reward-distributor-organization/tezos-reward-distributor
.. _Repo: https://github.com/tezos-reward-distributor-organization/trd-art
