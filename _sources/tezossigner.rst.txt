How to use the Tezos Signer
===========================

The payouts of the rewards are most frequently performed using an encrypted payment address. In order for the TRD to be able to sign the batch transactions, it should be able to communicate with the Tezos signer. Therefore, a prior configuration of the Tezos-signer is needed. 

There are three steps, first get the secret key of the payment address, second import the secret key to the signer, and finally start the http signer.

1. Get the secret key of the payment address. If the payment address was created using a wallet, please refer to the GUI/documentation of the used wallet to get the secret key of your payment address. If the payment address was created using the Tezos client, or if the secret key was previously imported to the Tezos Client, it can be obtained using the following command (Replace "`<myaddressalias>`" with your alias):
  ::

    ./tezos-client show address <myaddressalias> -S


2. Import the obtained secret key to the Tezos Signer. For that, you can replace "edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" with your encryped private key in the following command line: 
  ::

      ./tezos-signer import secret key <myaddressalias> encrypted:edesk1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

3. Launch the Tezos Signer. The following command will use the default IP address (127.0.0.1) and port (6732) of the Tezos signer, but these can be configured differently if desired by the user:
  ::

      ./tezos-signer launch http signer

Normally encrypted accounts are imported to the signer. So, it is necessary to provide the encryption password to the signer at launch. Note that the signer generates generic signatures e.g. sigXXXX but not edsigXXXX. For instructions on how to configure the signer on a docker image please go to the next section.
