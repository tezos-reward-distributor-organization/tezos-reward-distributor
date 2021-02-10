Payment Address
===============

TRD is designed to work as a linux service. It expects the usage of the Tezos signer for encrypted payment accounts. Unencrypted payment accounts can be used without tezos signer. If a payment account is encrypted and not configured to be signed by tezos signer, TRD will freeze.

An address can only be used for payments if it satisfies the following criteria:

- Public key of the address must be revealed. See tezos command line interface on how to run reveal command on tezos client. If an address is registered as delegate, there is no need to run reveal command.

  ::

      ./tezos-client reveal key for <alias>

- Secret key of the address must be known. If the payment address is an implicit address (tz), its secret key must be imported. If payment address is an originated address (KT), secret key of the manager address must be imported.

- If secret key is encrypted, tezos-signer must be used to sign payments. For instructions on how to use signer, please refer to the next section.

- Use of unencrypted secret key is also possible. The unencrypted secret key can be obtained from tezbox web wallet. An unencrypted secret key can be imported to the client using the command: 

  ::

      ./tezos-client import secret key <alias> unencrypted:edskXXXXX

For more information about tezos command line interface please refer to the official Tezos documentation_.

.. _documentation : https://tezos.gitlab.io/shell/cli-commands.html