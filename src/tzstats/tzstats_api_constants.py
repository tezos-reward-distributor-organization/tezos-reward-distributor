# https://tzstats.com/docs/api#income-table
# 0:    64698,            // row_id
# 1:    150,              // cycle
# 2:    278469,           // account_id
# 3:    3576,             // rolls
# 4:    3183854.077395,   // balance
# 5:    25426700.898205,  // delegated
# 6:    0,                // active_stake
# 7:    4,                // n_delegations
# 8:    199,              // n_baking_rights
# 9:    6507,             // n_endorsing_rights
# 10:    -292.000000,      // luck
# 11:    98.230000,        // luck_percent
# 12:    99.87,            // performance_percent
# 13:    100.00,           // contribution_percent
# 14:    201,              // n_blocks_baked
# 15:    201,              // n_blocks_proposed
# 16:    0,                // n_blocks_not_baked
# 17:    3293,             // n_blocks_endorsed
# 18:    0,                // n_blocks_not_endorsed
# 19:    6507,             // n_slots_endorsed
# 20:    15,               // n_seeds_revealed
# 21:    16198.000000,     // expected_income
# 22:    16176.875000,     // total_income
# 23:    519360.000000,    // total_deposits
# 24:    3216.000000,      // baking_income
# 25:    12959.000000,     // endorsing_income
# 26:    0.000000,         // accusation_income
# 27:    1.875000,         // seed_income
# 28:    1.680381,         // fees_income
# 29:    0,                // total_loss
# 30:    0,                // accusation_loss
# 31:    0,                // seed_loss
# 32:    0,                // endorsing_loss
# 33:    0,                // lost_accusation_fees
# 34:    0,                // lost_accusation_rewards
# 35:    0,                // lost_accusation_deposits
# 36:    0,                // lost_seed_fees
# 37:    0,                // lost_seed_rewards
# 38:    "tz2TSvNTh2epDMhZHrw73nV9piBX7kLZ9K9m",  // address
# 39:    1568887343000,    // start_time
# 40:    1569136305000     // end_time

# Income/Rewards Breakdown
idx_income_expected_income = 21
idx_income_total_income = 22

idx_income_baking_income = 24
idx_income_endorsing_income = 25
idx_income_accusation_income = 26
idx_income_seed_income = 27
idx_income_fees_income = 28
idx_income_missed_baking_income = 29  # Missing for now?
idx_income_missed_endorsing_income = 30  # Missing for now?
idx_income_stolen_baking_income = 31  # Missing for now?

idx_income_total_loss = 29
idx_income_lost_accusation_fees = 33
idx_income_lost_accusation_rewards = 34
idx_income_lost_accusation_deposits = 35
idx_income_lost_seed_fees = 36
idx_income_lost_seed_rewards = 37

# Rights
idx_n_blocks_baked = 14
idx_n_blocks_not_baked = 16
idx_n_active_stake = 6

# Cycle Snapshot
idx_balance = 0
idx_baker_delegated = 1
idx_delegator_address = 2

# Current balances
idx_cb_delegator_id = 0
idx_cb_current_balance = 1
idx_cb_delegator_address = 2
