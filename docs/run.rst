How to run TRD?
=====================================================

Command Line Usage
------------------------

The TRD can run with the following parameters:

::

    python3 src/main.py [-h] [-C INITIAL_CYCLE] [-M {1,2,3,4}] [-R RELEASE_OVERRIDE] [-O PAYMENT_OFFSET] [-N {MAINNET,DELPHINET}] [-A NODE_ENDPOINT] [-P {rpc,prpc,tzstats,tzkt}] [-Ap NODE_ADDR_PUBLIC] [-r REPORTS_BASE] [-f CONFIG_DIR] [-D] [-Dc] [-E SIGNER_ENDPOINT] [-d] [-s] [-Dp] [-V {on,off}] [-U API_BASE_URL] [-inj] [--syslog] [--log-file LOG_FILE]

It is adviseable to use the argument "-V on" in every run because it makes debugging easier.
The most common use case is to run in mainnet and start to make payouts from last released rewards or continue making payouts from the cycle last payment is done:

::

    python3 src/main.py -V on

Make payouts for a single cycle (300) and exit:

::

    python3 src/main.py -C 300 -M 3 -V on

Make all pending payouts and exit:

::

    python3 src/main.py -M 2 -V on

Make pending payouts beginning from a cycle and exit:

::

    python3 src/main.py -C 300 -M 2 -V on

Run in dry-run mode in delphinet, make payouts from cycle 300 and exit:

::

    python3 src/main.py -D -N DELPHINET -C 300 -M 3 -V on

Run in dry-run mode in mainnet, make payouts from cycle 300 onwards, for calculations use data provided by tezos node rpc interface:

::

    python3 src/main.py -C 300 -P rpc -D -V on

Run in dry-run mode in mainnet, make payouts for cycle 300, for calculations use data provided by the tzkt API:

::

    python3 src/main.py -C 300 -P tzkt -M 3 -V on -D

Run in dry-run mode in mainnet, retry failed payouts for cycle 300, for calculations use data provided by the tzstats API:

::

    python3 src/main.py -C 300 -P tzstats -M 4 -V on -D

For help, run

::

    python3 src/main.py -h

Explaination of individual arguments:

::

    -h                          # show help message and exit
    -C INITIAL_CYCLE            # First cycle to start payment. For last released rewards, set to 0. Non-positive values are interpreted as: current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1). If not set
                                # application will continue from last payment made or last reward released.
    -M {1,2,3,4}                # Waiting decision after making pending payments. 1: default option. Run forever. 2: Run all pending payments and exit. 3: Run for one cycle and exit. Suitable to use with -C option.
                                # 4: Retry failed payments and exit
    -R RELEASE_OVERRIDE         # Override NB_FREEZE_CYCLE value. last released payment cycle will be (current_cycle-(NB_FREEZE_CYCLE+1)-release_override). Suitable for future payments. For future payments give
                                # negative values. Valid range is [-11,)
    -O PAYMENT_OFFSET           # Number of blocks to wait after a cycle starts before starting payments. This can be useful because cycle beginnings may be busy.
    -N {MAINNET,DELPHINET}      # Network name. Default is MAINNET. The current test network of tezos is DELPHINET.
    -A NODE_ENDPOINT            # Node (host:port pair) potentially with protocol prefix especially if tls encryption is used. Default is http://127.0.0.1:8732. This is the main Tezos node used by the client for
                                # rpc queries and operation injections.
    -P {rpc,prpc,tzstats,tzkt}  # Source of reward data. The default is the use of a public archive rpc node, https://mainnet-tezos.giganode.io, to query all needed data for reward calculations. If you prefer to
                                # use your own local node defined with the -A flag for getting reward data please set the provider to rpc (the local node MUST be an ARCHIVE node in this case). If you prefer using a
                                # public rpc node, please set the node URL using the -Ap flag. An alternative for providing reward data is tzstats, but pay attention for license in case of COMMERCIAL use!
    -Ap NODE_ADDR_PUBLIC        # Public node base URL. This argument will only be used in case the provider is set to prpc. This node will only be used to query reward data and delegator list. It must be an
                                # ARCHIVE node. (Default is https://mainnet-tezos.giganode.io)
    -r REPORTS_BASE             # Directory to create reports
    -f CONFIG_DIR               # Directory to find baking configuration  
    -D                          # Run without injecting payments. Suitable for testing. Does not require locking.
    -Dc                         # Run without any consumers. Suitable for testing. Does not require locking.
    -E SIGNER_ENDPOINT          # URL used by the Tezos-signer to accept HTTP requests.
    -d                          # Docker installation flag. When set, docker script location should be set in -E
    -s                          # Marker to indicate that TRD is running in daemon mode. When not given it indicates that TRD is in interactive mode.
    -Dp                         # Do not publish anonymous usage statistics
    -V {on,off}                 # Produces a lot of logs. Good for trouble shooting. Verbose logs go into app_verbose log file. App verbose log file is named with cycle number and creation date. For each cycle a
                                # new file is created and old file is moved to archive_backup directory after being zipped.
    -U API_BASE_URL             # Base API url for non-rpc providers. If not set, public endpoints will be used.
    -inj                        # Try to pay injected payment items. Use this option only if you are sure that payment items were injected but not actually paid.
    --syslog                    # Log to syslog. Useful in daemon mode.
    --log-file LOG_FILE         # Log output file

Most arguements also have a verbose arguments if you prefer to work with those. You can find the verbose arguements in the help message. 