Anonymous Statistics
====================

The Tezos Reward Distributor collects anonymous statistics after each payout. These statistics are purely for analytical purposes e.g. to evaluate the prioritization of feature requests or to communicate the usage data for marketing purposes.

Nothing that TRD collects can be traced back to a specific delegate or delegator. The goal of the statistics is not to correlate nor discover specific bakeries that are using TRD.

* We *do not* collect any implicit or originated addresses.
* We *do not* collect any IP, or hostname related information.
* We *do not* generate identifiers using any address information.

If you wish to opt-out of this anonymous data collection, start TRD using the `--do_not_publish_stats` option.

If you have any questions about this topic or if you want to have access to the statistical data feel free to open an issue.

Collected Data
--------------

TRD collects the following statistics after each payout:

* Anonymous identifier
* Payout cycle
* Total payout amount
* Which network is in use (ie: mainnet, carthagenet, etc)
* Number of founders
* Number of owners
* Number of delegators
* Number of payments
* Number of failed transactions
* Number of injected transactions
* Number of attempts
* If baker pays transfer fee
* If baker pays reactivation fee
* If TRD is running as a background service
* Which RPC provider is in use
* Release override setting
* Payment offset setting
* If docker is being used
* Python version
* OS version
* TRD Version

Transfer
--------

A POST request is sent to the following AWS Lambda endpoint:

    https://jptpfltc1k.execute-api.us-west-2.amazonaws.com/trdstats

This endpoint does not collect any information about the source of the POST. No cookies are used.

GDPR
----

The General Data Protection Regulation, Recital 26 provides exception to anonymous and pseudonymous information.

Due to the anonymous nature of the collected data, TRD is within compliance of the GDPR.
