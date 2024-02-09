Tezos Reward Distributor (TRD)
======================================================

|Build Status| |Docs Status| |Stable Documentation Status|

DISCLAIMER : TEZOS REWARD DISTRIBUTOR IS PROVIDED AS IS. IT IS UNDER CONSTANT DEVELOPMENT. EVENT THOUGH IT IS WELL TESTED, PLEASE USE IT WITH CARE. ALWAYS MAKE A PRE-RUN IN DRY MODE BEFORE MAKING ACTUAL PAYMENTS. IF YOU WANT TO RUN IN SERVICE MODE DO IT AFTER YOU ARE CONFIDENT WITH THE APPLICATION. IN SERVICE MODE ONLY UPDATE IF NEEDED.

PRIVACY : TEZOS REWARD DISTRIBUTOR COLLECTS ANONYMOUS STATISTICS. PLEASE READ OUR STATISTICS POLICY_ FOR MORE INFORMATION.

What's TRD?
------------------------------------------------

TRD is an open-source software for distributing staking rewards from bakers to delegators introduced in detail in this Medium article_. This is not a python script but a full scale application which can continuously run in the background as a Linux service. However it does not have to be used as a service, but it can also be used interactively. The tool convinces with its simplicity and yet leaves no configuration wish unfulfilled. Whether minimum delegation threshold, special fees for some delegators, or actual vs ideal rewards - the TRD covers just about all possible constellations. Furthermore, the tool supports complex payments, pays in batches, and provides three back ends for calculations: Tezos RPC, tzpro_ API and TzKT_ API. TRD is developed and tested extensively by the community and the source code which can be found in the following Github_ repo.

Who needs TRD?
------------------------------------------------

The TRD is needed by bakers. There are a few payout tools available in the Tezos ecosystem. However, the TRD is probably the most used open source payout tool by bakers. It ranges from small bakers with a couple of delegators to large bakers with more than thousand delegators. The maintainers strive to keep up with the growing Tezos ecosystem. This in turn enables TRD users to participate in the exploration of new business areas like baking for liquidity pools or DAOs.

What else do you need for TRD?
------------------------------------------------

There are currently the following options to run TRD:

    a. If you want to use RPC (not public RPC) for the reward calculation, you need a Tezos archive node. 
    b. If you want to use an provider (pRPC, TZPRO, tzkt) for the reward calculation, but want to inject your own transactions, at least a Tezos rolling node is needed.
    c. If you want to use an provider (pRPC, TZPRO, tzkt) for the reward calculation and don't want to inject your own transactions, only the Tezos signer is needed.

However, for all options the Tezos signer is needed.

**Provider notes:**

Blockwatch: TZPRO
------------------

The terms_ of TZPRO note that an account and API key are needed for the use of the API. Please review the [pricing](https://tzpro.io/#pricing) information. For further help contact hello@blockwatch.cc for more information.

In order to use your API key in the application add it to your configuration like tzpro_api_key: XXXXXXXXXX.

TzKT
-----------

With PR232_ the backend of the Tezos Reward Distributor can be optionally `Powered by TzKT API`__ under the following terms:

    TzKT API is free for everyone and for both commercial and non-commercial usage.
    
    If your application or service uses the TzKT API in any forms: directly on frontend or indirectly on backend, you should mention that fact on your website or application by placing the label "Powered by TzKT API" with a direct link to tzkt.io.

.. _POLICY : statistics.html

.. _article : https://medium.com/@huseyinabanox/tezos-reward-distributor-e6588c4d27e7

.. _tzpro: https://tzpro.io/

.. _TzKT : https://api.tzkt.io/

.. _terms : https://tzpro.io/terms

.. _Github : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor

.. _PR232 : https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/pull/232

.. _API : https://tzkt.io/

__ API_

Funding
------------------------

TRD is an open source, GPL licensed project. It is maintained by various community members.

TRD Art Work
------------------------

This Github Repo_ contains logo images. If you are using TRD and want to let everybody know about it, feel free to place them in your website.

.. |Build Status| image:: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/CI/badge.svg
   :target: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions
.. |Docs Status| image:: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/workflows/Docs/badge.svg
   :target: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/actions
.. _Repo: https://github.com/tezos-reward-distributor-organization/trd-art
.. |Stable Documentation Status| image:: https://img.shields.io/badge/docs-stable-blue.svg
   :target: https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/

.. toctree::
   :maxdepth: 2
   :caption: Content:

   installation
   configuration
   paymentaddress
   tezossigner
   run
   rundocker
   payouttiming
   plugins
   linuxservice
   state_machine
   contributors
   multisig_payouts
   testing
   statistics
   codeofconduct
