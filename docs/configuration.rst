How to configure TRD?
==========================================

Fee Setup
------------------------

fee.ini file contains details about transaction fees. Currently the fee value specified under DEFAULT domain is used as fee amount. It is in mutez.

Baker Configuration:
--------------------

Each baker has its own configuration and policy. Therefore, a payment system should be flexible enough to cover the needs of bakers. The application uses a yaml file for loading baker specific configurations and is loaded at every start.
There are two options to create a custom yaml file:

    a. You can use the interactive configuration tool (configure.py)
    b. You can copy&paste the example config from ~/tezos-reward-distributor/examples into ~/pymnt/cfg, rename and change it according to your baker policy.

If you want to use Option a, you can use
::

    # Move into tezos-reward-distributor directory
    cd tezos-reward-distributor
    # Run the interactive configuration tool
    python3 src/configure.py

If you want to use Option b, you can use
::

    # create directory
    mkdir -p ~/pymnt/cfg/
    # Copy & Paste
    cp tezos-reward-distributor/examples/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml ~/pymnt/cfg/
    # Edit the file with nano
    nano ~/pymnt/cfg/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml

By default, configuration files are kept under ~/pymnt/cfg directory. The configuration directory can be changed with "-f" configuration option. The name of a configuration file should be the baker's address (e.g. tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml).
If you want to use with a decimal operator within your config, please use a decimal point. 

Available configuration parameters are:

**baking_address**
  Address of the baker. It must be an implicit account (tz1). No alias is allowed.

  Example::

    baking_address: tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889
  
**payment_address**
  This is the address where payments will be done from. A PKH of implicit or originated account is accepted. For more information on the payment address configuration please refer to the next section. No alias is allowed.

  Example::

    payment_address: tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889

**rewards_type**
  There are two options for calculating the total rewards earned by a baker at the end of each cycle. If this parameter is missing, 'actual' rewards take affect.
  
  'ideal': Rewards are calculated using the number of baking rights granted at priority 0, plus the count of all endorsing slots. If a bake or endorsement is missed, rewards are calculated as if there was no miss. No additional block rewards or transaction fees are included in this method.
  'actual': Rewards are calculated based on the actual number of bakes, at any priority, and any endorsements. If a bake or endorsement is missed, rewards are not earned and therefor not included. Transaction fees and other block rewards are included in the rewards.

  Example::

    rewards_type: actual

  Note that 'actual' payouts will throw an error if:

#. The 'RELEASE_OVERRIDE' parameter is set to a value inferior or equal to -5, since the payouts are done before the cycle is completed, or
#. The 'RELEASE_OVERRIDE' parameter is set to a value inferior or equal to -1, and the backend API is a Tezos node RPC, as actual payout calculation in this context is not implemented.

**service_fee**
  A decimal in range [0-100]. Also known as the baker's fee. This is evaluated as a percentage value. Example: If set to 5, then 5% of baking rewards are kept as a service fee by the baker.

  Example::

    service_fee: 10

**founders_map**
  A dictionary of PKH and ratio (decimal in the range [0-1]) pairs. Each item in this dictionary represents PKH of each founder and his ratio of the shares coming from the service fee. Implicit or originated addresses are accepted. It is important that the sum of all ratios equals to 1. This map is optional if founders do not want to be paid from service fees, in this case, service fee remains in baking balance.
  
  Example::

    founders_map:
        {'tz3VxS7ff4YnZRs8b4mMP4WaMVpoQjuo1rjf' : 0.6,
         'tz1PirboZKFVqkfE45hVLpkpXaZtLk3mqC17' : 0.4}
  
  Alice and Bob are both founders of Acme Bakery. Their bakery fee is 10%. Alice has a 60% (0.6) interest in the bakery, and Bob has a 40% (0.4) interest. When rewards are delivered at the end of each cycle, 10% is taken as the bakery fee (ie: *service_fee*). That 10% is then divided between Alice and Bob according to their ratios.
  
**owners_map**
  A dictionary of PKH and ratio ( decimal in the range [0-1]) pairs. Each item in this dictionary represents PKH of each balance owner and his ratio of the amount he owns in the total baking balance. Implicit or originated addresses are accepted. It is important that the sum of all ratios equals to 1. This map is optional if owners do not want to be paid for baking rewards, in this case, baking rewards remain in baking balance.
  
  Example::

    Current Baker Balance: 17,400 XTZ
    Total Delegations: 69,520 XTZ
    Total Staked: 86,920 XTZ

    service_fee: 9
    owners_map:
      {'tz1PV5g16m9hHMAVJ4Hx6NzzUHgksDnTLFcK' : 0.4,
       'tz1PirboZKFVqkfE45hVLpkpXaZtLk3mqC17' : 0.4,
       'tz1VxS7ff4YnZRs8b4mMP4WaMVpoQjuo1rjf' : 0.2}
  
  Charlie, and Dave, have each transfered 6,960 Tez to the baker address. Edwin has transfered 3,480 Tez. They are each partial owners of the baking balance. When rewards are delivered at the end of each cycle, 9% is taken as the bakery fee (ie: *service_fee*). That 9% is dispersed to any *founders*. If there are no founders, that 9% remains in the baker's balance.
  The baker address is technically a delegator to itself. Its share of rewards are part of the overall cycle rewards. Charlie, Dave, and Edwin divide the "baker address rewards" as per the ratios in *owners_map*. Additionally, owners are *not* subject to the *service_fee*.

**specials_map**
  A dictionary of PKH and fee (decimal in the range [0-100] ) pairs. This dictionary can be used to set special service fee values for desired delegators.

  Example::

    specials_map : {'tz3VxS7ff4YnZRs8b4mMP4WaMVpoQjuo1rjf' : 5,
                    'tz1PirboZKFVqkfE45hVLpkpXaZtLk3mqC17' : 5}
  
**supporters_set**
  A set of PKH values. Each PKH represents a supporter of the baker. Supporters are not charged with a service fee. Founders and balance owners are natural supporters, they are not needed to be added.

  Example::

    supporters_set : {'tz3VxS7ff4YnZRs8b4mMP4WaMVpoQjuo1rjf',
                    'tz1PirboZKFVqkfE45hVLpkpXaZtLk3mqC17'}

**min_delegation_amt**
  A minimum delegation amount can be set here. If this value is set to 10, 10 XTZ are required as minimum. It is important to define what happens to the rewards of excluded delegates that are below the minimum delegation balance in rules_map.

  Example::

    min_delegation_amt : 10
  
**reactivate_zeroed**
  True/False - If True, an account to be paid found with a 0 balance will be reactivated, incurring the necessary burn fee and storage, and rewards will be sent. If False, any account with a 0 balance will be skipped payment. This will be noted in the CSV report.

  Example::

    reactivate_zeroed : True
  
**delegator_pays_xfer_fee**
  Default value is true. If set to false, the transfer fee for each payment is paid by the delegate. Otherwise, the transfer fee is deducted from the delegator reward.

  Example::

    delegator_pays_xfer_fee : False

**delegator_pays_ra_fee**
  True/False - Functions just like delegator_pays_xfer_fee, except refers to the burn/reactivation fee. If True, the burn fee is subtracted from the reward payment (ie: delegate pays). If False, burn fee is paid for by baker. If reactivate_zeroed: True and delegator_pays_ra_fee: True but the reward is smaller than the burn fee, their rewards will be ignored and will simply remain at the bakers address.

  Example::

    delegator_pays_ra_fee : False

**rules_map**
  The rules_map is needed to redirect payments. A pre-defined source (left side) is mindelegation. Pre-defined destinations (right side) are: TOF = to founders balance, TOB = to bakers balance, and TOE = to everyone. Variable sources and destinations are PKHs. New since v8.0 PKH: Dexter enables payouts to Dexter liquidity pools.

  Example::

     rules_map:
       tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ: TOF                                         #(redirects payment from tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ to founders)
       tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace: TOB                                         #(payment to tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace will remain in the bakers balance)
       tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT: tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7        #(redirects payment from tz1V9S... to tz1fgX...)
       tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs: Dexter                                      #(indicates address is a dexter pool; TRD will send rewards to pool members)
       mindelegation: TOE                                                                #(mindelegation will be shared with everyone)
  
**plugins**
  Please consult the `plugins docs`_ for more details on the configuring the various plugins.

.. _plugins docs : plugins.html