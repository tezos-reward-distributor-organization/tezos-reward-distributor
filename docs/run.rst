How to run TRD
==============

Command Line Usage
------------------

::

    python3 src/main.py [-h] (for list of options)

::

    python3 src/main.py [options]

Options
-------

``-h``
    Show help message and exit.

``-C --initial_cycle <int>``
    Cycle to start payment(s) from. Valid range: ``[-1,)``. Default value: ``-1`` (pay rewards that were most recently released). Cycle for which rewards were most recently released is calulated based on the formula: ``current_cycle - (NB_FREEZE_CYCLE+1) - release_override``.

``-M --run_mode <int>``
    Waiting decision after making pending payments. Valid range: ``[1,4]``. Default value: ``1``. Values description:

    1. Run forever.
    2. Run all pending payments and exit.
    3. Run for one cycle and exit. Suitable to use with ``-C`` option.
    4. Retry failed payments and exit.

``-R --release_override <int>``
    Override ``NB_FREEZE_CYCLE`` value, which is 5 by default. Valid range is ``[-11,-1]``. Default value: ``0`` (with no effect). Last released payment cycle will be calculated based on the formula: ``current_cycle - (NB_FREEZE_CYCLE+1) - release_override``. Suitable for future payments providing a negative value.

``-O --payment_offset <int>``
    Number of blocks to wait after a cycle starts before starting payments. This can be useful because cycle beginnings may be busy.

``-N --network <MAINNET|FLORENCENET>``
    Network name. Default value: ``MAINNET``. The current test network of Tezos is ``FLORENCENET``.

``-A --node_endpoint <node_url:port>``
    Node potentially with protocol prefix especially if TLS encryption is used. Default value: ``http://127.0.0.1:8732``. This is the main Tezos node used by the client for RPC queries and operation injections.

``-P --reward_data_provider <rpc|prpc|tzstats|tzkt>``
    Source that provides all needed data for reward calculations. Default value: ``prpc``. If you prefer to use your own local node, defined with the ``-A`` option, for getting reward data you must set this option to ``rpc`` (the local node must be an archive node in this case). If you prefer using a public RPC node, please set the node URL using the ``-Ap`` option. An alternative for providing reward data is ``tzstats``, but pay attention for license in case of COMMERCIAL use!

``-Ap --node_addr_public <url>``
    Public node base URL. Default value: ``https://mainnet-tezos.giganode.io``. This argument will only be used in case the provider is set to `prpc`. This node will only be used to query reward data and delegator list. It must be an archive node.

``-r --reports_base <path>``
    Directory to create reports. Default value: ``~/pymnt/reports``.

``-f --config_dir <path>``
    Directory to find baking configuration. Default value: ``~/pymnt/cfg``.

``-D --dry_run``
    Run without injecting payments. Suitable for testing. Does not require locking.

``-Dc --dry_run_no_consumers``
    Run without any consumers. Suitable for testing. Does not require locking.

``-E --signer_endpoint <url>``
    URL used by the Tezos signer to accept HTTP(S) requests. Default value: ``http://127.0.0.1:6732``.

``-d --docker``
    Docker installation flag. When set, docker script location should be set in ``-E``.

``-s --background_service``
    Marker to indicate that TRD is running in daemon mode. When not given it indicates that TRD is in interactive mode.

``-Dp --do_not_publish_stats``
    Do not publish anonymous usage statistics.

``-V --verbose <on|off>``
    Produces a lot of logs. Default value: ``on``. Good for troubleshooting. Verbose logs go into app_verbose log file. App verbose log file is named with cycle number and creation date. For each cycle a new file is created and old file is moved to archive_backup directory after being zipped.

``-U --api_base_url``
    Base API URL for non-RPC providers. If not set, public endpoints will be used.

``-inj --retry_injected``
    Try to pay injected payment items. Use this option only if you are sure that payment items were injected but not actually paid.

``--syslog``
    Log to syslog. Useful in daemon mode.

``--log-file <path>``
    Log output file.

Examples
--------

It is adviseable to use the verbose argument ``-V`` on every run because it makes debugging easier.

The most common use case is to run on ``MAINNET`` and start to make payouts from last released rewards or continue making payouts from the cycle last payment is done:

::

    python3 src/main.py -V

Make payouts for a single cycle and exit:

::

    python3 src/main.py -C 300 -M 3 -V

Make all pending payouts and exit:

::

    python3 src/main.py -M 2 -V

Make pending payouts beginning from a cycle and exit:

::

    python3 src/main.py -C 300 -M 2 -V

Run in dry-run mode on FLORENCENET, make payouts for cycle 300 and exit:

::

    python3 src/main.py -D -N FLORENCENET -C 300 -M 3 -V

Run in dry-run mode on MAINNET, make payouts from cycle 300 onwards, for calculations use data provided by Tezos node RPC interface:

::

    python3 src/main.py -C 300 -P rpc -D -V

Run in dry-run mode on MAINNET, make payouts only for cycle 300, for calculations use data provided by the TzKT API:

::

    python3 src/main.py -C 300 -P tzkt -M 3 -V -D

Run in dry-run mode on MAINNET, retry failed payouts only for cycle 300, for calculations use data provided by the TzStats API:

::

    python3 src/main.py -C 300 -P tzstats -M 4 -V -D

For help, run:

::

    python3 src/main.py -h
