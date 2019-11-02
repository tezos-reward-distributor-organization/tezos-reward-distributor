
How to configure Tezos Reward Distributor?
=====================================================

Baker Configuration:
------------------------

Each baker has its own configuration and policy. A payment system should
be flexible enough to cover needs of bakers. The application uses a yaml
file for loading baker specific configurations.

Configuration tool can be used to create baking configuration file
interactively. Also an example configuration file is present under
examples directory. For more information on configuration details, please
see our wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/Configuration>`_.

TRD is designed to work as a linux service. It expects use of tezos
signer for encrypted payment accounts. Unencrypted payment accounts can
be used without tezos signer. If a payment account is encrypted and not
configured to be signed by tezos signer, TRD will freeze. For more
information on payment addresses please refer to our wiki `page <https://github.com/habanoz/tezos-reward-distributor/wiki/Payment-Address>`_.

Email Setup
------------------------

Get emails for payment reports at each cycle. Fill email.ini file with
your email details to receive payment emails.

Fee Setup
------------------------

fee.ini file contains details about transaction fees. Currently the fee
value specified under DEFAULT domain is used as fee amount. It is in
mutez.

