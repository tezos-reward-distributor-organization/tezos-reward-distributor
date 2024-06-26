.. _payout_timing:

Payout timing
=============

Tezos rewards are paid out by the protocol at the end of a given cycle.

By default, TRD then distributes these rewards at the beginning of the next cycle.

TRD behavior is to pay out the last released payment cycle. Last
released payment cycle will be calculated based on the formula:
``current_cycle - 1 + [if --adjusted_payout_timing is provided: (preserved_cycles + 1)]``.

A cycle on mainnet lists 3 days.

Delegation takes 2 cycles to take effect. This is unlike staking, which is instantaneous.
