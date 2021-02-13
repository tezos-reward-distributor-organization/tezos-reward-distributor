How to use the Tezos Signer (WIP)
===========================

Tezos signer daemon can be configured to sign the operations with the secret key of the account. There are two steps, first import secret key to the signer, second tell the client that it can use particular signer to sign the operations.

1. Configure Signer

  Replace "`<myaddressalias>`" with your alias. Replace "edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" with your encryped private key. IP address and port selection are up to the user.

  ::

      ./tezos-signer import secret key <myaddressalias> encrypted:edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
      ./tezos-signer launch socket signer -a 127.0.0.1 -p 22000 -W

2. Configure Client

  Replace "`<myaddressalias>`" with your alias. Replace "`<PKH>`" with your public key hash. Use the same host port combination from the previous step.

  ::

    ./tezos-client import secret key <myaddressalias> tcp://127.0.0.1:22000/<PKH> -f

When the client is required to sign an operation, the operation is sent to the signer. Signer generates a signature and sends back to the client. Normally encrypted accounts are imported to the signer. So, it is necessary to provide encryption password to the signer at launch. Note that signer generates generic signatures e.g. sigXXXX but not edsigXXXX. For instructions on how to configure signer on a docker image go to the next section.
 
