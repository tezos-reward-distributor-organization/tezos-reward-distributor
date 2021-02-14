Tezos Signer with Docker (WIP)
========================

**IMPORTANT: This section is still under maintenance. This will be updated parallely to adding the docker support to the TRD**

In Tezos *mainnet* it is not safe to keep private keys unencrypted. Many use HSM (Hardware Security Module) to keep private keys. Luckily HSMs are not the only option. The Tezos Signer can be used to sign transactions/blocks. Tezos-signer should be given encrypted private key so that it can sign operations. For security reasons tezos-signer does not keep encryption password anywhere, it must be typed upon tezos-signer launch. As a result, it is not possible to run tezos-signer as a daemon. 

The Tezos Signer must be run from shell interactively and encryption password must be typed. Then this shell session must be kept open otherwise tezos-signer process dies. However, if baking service is in the cloud then it is not practical to keep a terminal session open. 

The proposed solution is to use Tezos docker image in host network mode. Start the signer and type the password. Terminate the terminal session. Signer will continue to work and sign operations.

DISCLAIMER: SAFETY OF THE PROPOSED METHOD IS NOT ASSURED. USE OF HSM IS ADVISED. IF AN ATTACKER BREACHES THE MACHINE TEZOS SIGNER RUNNING IT MAY COPY YOU PRIVATE KEY FROM EZOS SIGNER MEMORY. IN DEFAULT MODE TEZOS SIGNER MAY BE USED BY THE ATTACKER TO SIGN ANY TRANSACTIONS INCLUDING TEZOS TRANSFERS. BEFORE USING THIS METHOD BEWARE OF THE DANGERS.

**IMPORTANT:**

This need to be tested again for the current version of the Tezos test network. Some commands and filenames may have changed!

1 - Setup Tezos Docker Image
----------------------------

Example command is for *babylonnet*:

::

    wget -O babylonnet.sh https://gitlab.com/tezos/tezos/raw/babylonnet/scripts/alphanet.sh
    chmod +x babylonnet.sh
    ./babylonnet.sh start
    ./babylonnet.sh status

For mainnet, replace first "babylonnet.sh" with "mainnet.sh" and have a look at the official Tezos docker_ documentation.

2 - Configure Tezos Signer
--------------------------

For mainnet replace "babylonnet" with "mainnet". Replace "myaddressalias" with your alias. Replace "edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" with your encryped private key. Replace "8fa665779b7b" with result from docker ps.

::

    docker run -it  tezos/tezos:babylonnet tezos-signer import secret key mykeyalias encrypted:edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    docker ps -a
    docker commit 8fa665779b7b tezos-babylonnet-signer
    docker run --net=host -it tezos-babylonnet-signer tezos-signer launch socket signer -a 127.0.0.1 -p 22000 -W

3 - Configure Tezos Client
--------------------------

Replace "myaddressalias" with your alias. Replace "tz1PKH" with your public key hash. It is up to you to select host IP and port.

::

    ./tezos-client import secret key myaddressalias tcp://127.0.0.1:22000/tz1PKH -f

4 - Configure baker and endorser
--------------------------------

Replace "myaddressalias" with your alias. Replace "tz1PKH" with your public key hash. "~/.tezos-node/" is where node data is stored and may be different in your system. Also, baker/endorser binary name may change according to currently active protocol.

::

    ./tezos-baker-003-PsddFKi3 -R tcp://127.0.0.1:22000/tz1PKH run with local node ~/.tezos-node/ myaddressalias
    ./tezos-endorser-003-PsddFKi3 -R tcp://127.0.0.1:22000/tz1PKH run myaddressalias

5 - Test
--------

To make sure that tezos-signer can survive terminal session death, run tests after terminating the session the signer is launched.

You must see tezos-signer process after running following command.

::

    ps -ef | grep tezos-signer

Transfer small amount of money from your account to make sure that tezos-signer is signing operations.

::

    ./tezos-client transfer 1 from myaddressalias to someaddress --fee 0

.. _docker : http://tezos.gitlab.io/introduction/howtoget.html?highlight=docker#docker-images
