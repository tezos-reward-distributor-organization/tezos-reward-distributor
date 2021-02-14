Payment Address
===============

TRD is designed to work as a linux service. It expects the usage of the Tezos signer for encrypted payment accounts.

An address can only be used for payments if it satisfies the following criteria:

- The public key of the address must be revealed. See the Tezos command line interface on how to run reveal command using the Tezos client e.g. If an address is registered as delegate, there is no need to run the reveal command.

  ::

      ./tezos-client reveal key for <alias>

- The payment address must be an implicit address (tz). The secret key of the address must be known and imported to the signer before running the TRD. Please refer to the Tezos signer section for detailed instructions. 
