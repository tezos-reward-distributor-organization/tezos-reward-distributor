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
    Cycle to start payment(s) from. Valid range: ``[-1,)``. Default value: ``-1`` (pay rewards that were most recently released). Cycle for which rewards were most recently released is calculated based on the formula: ``current_cycle - 1 + [if --adjusted_payout_timing == True: (preserved_cycles + 1)]``.

``-M --run_mode <int>``
    Waiting decision after making pending payments. Valid range: ``[1,4]``. Default value: ``1``. Values description:

    1. Run forever.
    2. Run all pending payments and exit.
    3. Run for one cycle and exit. Suitable to use with ``-C`` option.
    4. Retry failed payments and exit.

``--adjusted_early_payouts``
    If provided allows for early, later on adjusted payouts for cycle = current_cycle - 1 + (preserved_cycles + 1). Its default value is ``False`` if not provided as argument. See :ref:`payout_timing`.

``-O --payment_offset <int>``
    Number of blocks to wait after a cycle starts before starting payments. This can be useful because cycle beginnings may be busy.

``-N --network <MAINNET|GHOSTNET>``
    Network name. Default value: ``MAINNET``. The current test network of Tezos is ``GHOSTNET``.

``-A --node_endpoint <node_url:port>``
    Node potentially with protocol prefix especially if TLS encryption is used. Default value: ``http://127.0.0.1:8732``. This is the main Tezos node used by the client for RPC queries and operation injections.

``-P --reward_data_provider <rpc|prpc|tzpro|tzkt>``
    Source that provides all needed data for reward calculations. Default value: ``tzkt`` (TzKT API). Set to ``rpc`` to use your own local node defined with the ``-A`` flag, (it must be an ARCHIVE node in this case). Set to ``prpc`` to use a public RPC node defined with the ``-Ap`` flag. An alternative for providing reward data is ``tzpro``, but an API key associated with your account needs to be provided in the .env file!

``-Ap --node_addr_public <url>``
    Public node base URL. Default is ``https://mainnet.smartpy.io``. This argument will only be used in case the reward provider is set to ``prpc``. This node will only be used to query reward data and delegator list. It must be an ARCHIVE node.

``-b --base_directory <path>``
    Directory for reports, configuration and logs. Default value: ``~/pymnt``.
    The directory contains the following folders:
    
    1. ~/pymnt/cfg
    2. ~/pymnt/simulations
    3. ~/pymnt/reports
    4. ~/pymnt/logs

``-D --dry_run``
    Run without injecting payments. Suitable for testing. Does not require locking.

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

``--log_file <path>``
    Application log output folder path and file name. By default the logs are placed into the --base_directory e.g.:: ``~/pymnt/logs/app.log``.

Examples
--------

It is adviseable to use the verbose argument ``-V`` on every run because it makes debugging easier.

The most common use case is to run on ``MAINNET`` and start to make payouts from last released rewards or continue making payouts from the cycle last payment is done:

::

    python3 src/main.py -V

Make payouts for a single cycle and exit:

::

    python3 src/main.py -C 300 -M 3 -V

Make all pending payouts from last released cycle and exit:

::

    python3 src/main.py -M 2 -V

Make pending payouts beginning from a cycle and exit:

::

    python3 src/main.py -C 300 -M 2 -V

Run in dry-run mode on GRANADANET, make payouts for cycle 300 and exit:

::

    python3 src/main.py -D -N GRANADANET -C 300 -M 3 -V

Run in dry-run mode on MAINNET, make payouts from cycle 300 onwards, for calculations use data provided by local Tezos node RPC interface:

::

    python3 src/main.py -C 300 -P rpc -D -V

Run in dry-run mode on MAINNET, make payouts only for cycle 300, for calculations use data provided by the public node RPC:

::

    python3 src/main.py -C 300 -P prpc -Ap https://mainnet.smartpy.io -M 3 -V -D

Run in dry-run mode on MAINNET, retry failed payouts only for cycle 300, for calculations use data provided by the TZPRO API:

::

    python3 src/main.py -C 300 -P tzpro -M 4 -V -D

For help, run:

::

    python3 src/main.py -h
