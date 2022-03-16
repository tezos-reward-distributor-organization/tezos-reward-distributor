.. _payout_timing:

Payout timing
=============

Tezos rewards are paid out by the protocol at the end of a given cycle,
and are unfrozen 5 cycles later.

Should the baker decide to pay out rewards after they are unfrozen,
their delegators will have to wait 12 cycles to get their first payout.

This is TRD default behavior, however many bakers elect to pay out
rewards before they are unfrozen.

Bakers may elect to pay their delegators early to appear more
competitive or trustworthy. But bakers paying early effectively give an “advance” to their delegators.
This means that they have a lower balance at any given point in time.


TRD behavior is to pay out the last released payment cycle. Last
released payment cycle will be calculated based on the formula:
``current_cycle - (NB_FREEZE_CYCLE+1) - release_override``.

``NB_FREEZE_CYCLE`` is 5 on mainnet. A cycle on mainnet lasts 3 days.

The ``--release_override`` ``-R`` parameter lets the baker override when rewards
are released (paid out). Its default value is 0.

Possible choices are:

-  ``0``: pay rewards when they are unfrozen - 11 to 12 cycles after delegation.
-  ``-5``: pay rewards after the cycle runs (a popular choice amongst bakers) - 7 to 8 cycles after delegation.
-  ``-11``: pay rewards when baking rights are assigned, referred as “adjusted
   early payouts” (see below) - 2 to 3 cycles after delegation.

Adjusted early payouts
----------------------

A ``release_override`` of ``-11`` will trigger adjusted early payouts.

When selected, this option calculates and pays out the expected rewards based on baking and
endorsing rights only. It does not takes into account fee income,
denunciation income or rescued block income. It also assumes perfect
behavior of the baker and other bakers.

The resulting rewards are thus an estimation. When the cycle
actually runs, TRD runs the calculations for this cycle again, based on
the rewards type configured (ideal or actual). It then computes the
“overestimate” or overpaid value.

TRD then attempts to claim back this overestimate by adjusting the
amount paid. **This does not always work**. If the delegator has emptied
their account or changed delegate, there is no longer any payout to
offset a past overestimate. Thus, users are advised caution when using
this feature.

The estimate can also be lower than the final amount, for example if fees were earned in excess of the missed income, or if blocks have been rescued by the baker. In this case, the overestimate will show a negative amount, the delegator has been underpaid and will be compensated with a positive adjustment.

Overestimate, adjustment and adjusted amount paid can be seen in the
calculations CSV file.

**Example:**

**Cycle 100**: Frank and Cindy both delegate 1000 tez to Jane’s bakery. For
simplicity, Jane’s bakery has no fee and no other delegators. Her bakery is
configured with a ``release_override`` of ``-11`` and ``rewards_type`` ``actual``.

**Cycle 103**: Since ``release_override`` is set to ``-11``, payout for cycle 108 happens during cycle 103. Frank and Cindy’s delegation is taken into account to compute
cylce 108’s rights. Jane’s bakery is expected to earn 25 tez rewards for
cycle 108 from baking and endorsing rewards. Frank and Cindy contribute 10% each to Jane’s staking
balance. They each receive 2.5 tez as part of the payout for cycle 108.

A ``calculations/108.csv`` file is generated which shows ``Overestimate:
pending`` as cycle 108 has not run yet.

**Cycle 104-108**: same as cycle 103: Frank and Cindy receive 10% each of the estimated reward..

**Cycle 109**: Jane’s bakery is expected to earn 15 tez from baking and endorsing rewards for cycle 114, so
each delegator should be paid 1.5 tez. TRD runs the calculations for
cycle 108 again and finds that Jane earned 0.5 tez fee for baking a
block. She also missed some endorsements and did not earn 0.75 tez.
Overall, Jane’s bakery overestimated its earnings by 0.25 tez, or 1%.
It therefore substracts 1% of cycle 108 payout to cycle 114 payout (which happens at cycle 109).
Frank and Cindy receive 1.475 tez as adjusted amount for cycle 114.

``calculations/108.csv`` file is updated with a total overestimate of 0.25
and their distribution across delegates: 0.025 tez for Frank and for
Cindy. ``calculations/114.csv`` file mentions an adjustment of 0.025 tez for
Frank and Cindy.

Had Frank left the bakery at cycle 104, Jane’s bakery would have been
unable to recover his overpaid 0.025 tez.
