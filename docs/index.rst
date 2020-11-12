Tezos Reward Distributor (Run & Forget) |Build Status|
======================================================

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS.
IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL
TESTED, PLEASE USE IT WITH CARE. ALWAYS MAKE A PRE-RUN IN
DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO
RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH
THE APPLICATION. IN SERVICE MODE ONLY UPDATE IF NEEDED.

PRIVACY : TEZOS REWARD DISTRIBUTOR COLLECTS ANONYMOUS
STATISTICS. PLEASE READ OUR STATISTICS POLICY_ FOR MORE
INFORMATION.

What is Tezos Reward Distributor?
------------------------------------------------

TRD is a software for distributing staking rewards of
delegators introduced in detail in this Medium article_.
This is not a script but a full scale application which
can continuously run in the background as a Linux service.
It can track cycles and make payments. However it does
not have to be used as a service, but it can also be
used interactively.

TRD supports complex payments, pays in batches, and provides
three back ends for calculations: Tezos RPC, tzstats_ API and
TzKT_ API. TRD is developed and tested extensively by the community
and the source code which can be found in the following Github_ repo.

**Provider notes:**

TZStats
-----------

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

TzKT
-----------

With #232_ the backend of the Tezos Reward Distributor
can be optionally **Powered by TzKT API_** under the
following terms:

> TzKT API is free for everyone and for both commercial
> and non-commercial usage.
>
> If your application or service uses the TzKT API in
> any forms: directly on frontend or indirectly on
> backend, you should mention that fact on your website or
> application by placing the label "Powered by TzKT API"
> with a direct link to tzkt.io.

.. _POLICY : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/blob/master/docs/statistics.rst

.. _article : https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7

.. _tzstats : https://tzstats.com/

.. _TzKT : https://api.tzkt.io/

.. _terms : https://tzstats.com/terms

.. _Github : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor

.. _#232 : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/pull/232

.. _API : https://tzkt.io/

.. toctree::
   :maxdepth: 2
   :caption: Tezos Reward Distributor:

   installation
   configuration
   plugins
   paymentaddress
   tezossigner
   tezossignerdocker
   run
   linuxservice
   statistics
   contributors

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
