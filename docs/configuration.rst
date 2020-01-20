How to configure Tezos Reward Distributor?
==========================================

Email Setup
------------------------

Get emails for payment reports at each cycle. Fill email.ini file with
your email details to receive payment emails.

Fee Setup
------------------------

fee.ini file contains details about transaction fees. Currently the fee
value specified under DEFAULT domain is used as fee amount. It is in
mutez.

Baker Configuration:
--------------------

Each baker has its own configuration and policy. A payment system should
be flexible enough to cover the needs of bakers. The application uses a yaml
file for loading baker specific configurations.

Configuration tool can be used to create baking configuration file
interactively. Also an example configuration file is present under
examples directory.
By default configuration files are kept under ~/pymnt/cfg directory.
Configuration directory can be changed with "-f" configuration option.
Name of a configuration file should be the baker's address
(e.g. tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml).

You can use configure.py tool to interactively create your configuration
file, with ease.

Available configuration parameters are:

**baking_address**
  Address of the baker. It must be an implicit account (tz1).
  No alias is allowed.
  
**payment_address**
  This is the address where payments will be done from. A PKH
  or alias of implicit or originated account is accepted. For
  more information on the payment address configuration please
  refer to the next section.
  
**service_fee**
  A decimal in range [0-100]. This is evaluated as a percentage
  value. If this value is set to 5, 5% of baking rewards are
  kept as a service fee.

**founders_map**
  A dictionary of PKH and ratio (decimal in the range [0-1])
  pairs. Each item in this dictionary represents PKH of each
  founder and his ratio of the shares coming from service fees.
  Implicit or originated addresses are accepted. It is important
  that the sum of all ratios equals to 1. This map is optional
  if founders do not want to be paid from service fees, in
  this case, service fee remains in baking balance.
  
**owners_map**
  A dictionary of PKH and ratio ( decimal in the range [0-1])
  pairs. Each item in this dictionary represents PKH of each
  balance owner and his ratio of the amount he owned in the
  total baking balance. Implicit or originated addresses are
  accepted. It is important that the sum of all ratios equals
  to 1. This map is optional if owners do not want to be paid
  for baking rewards, in this case, service fee remains in
  baking balance.

**specials_map**
  A dictionary of PKH and fee (decimal in the range [0-100] )
  pairs. This dictionary can be used to set special service
  fee values for desired delegators.
  
**supporters_set**
  A set of PKH values. Each PKH represents a supporter of the
  baker. Supporters are not charged with a service fee. Founders
  and balance owners are natural supporters, they are not
  needed to be added.

**min_delegation_amt**
 A minimum delegation amount can be set here. If this value is set 
 to 10, 10 XTZ are required as minimum.
  
**delegator_pays_xfer_fee**
  Default value is true. If set to false, the transfer fee for
  each payment is paid by the delegate. Otherwise, the transfer
  fee is deducted from the delegator reward.

**rules_map**
  The rules_map is needed to redirect payments. Constants are TOF = To Founders Balance, 
  TOB = To Bakers Balance and mindelegation.
  
  Example: 
  rule_map:
  PKH: TOF (redirects payment from PKH to TOF)
  PHK: TOB (payment will be kept in the baking_address)
  PKH: PKH (redirects payment from PKH to PKH)
  mindelegation: TOB (mindelegation will be kept in the baking_address)
  
