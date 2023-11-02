import os
from dotenv import load_dotenv
from log_config import verbose_logger

# TODO: Check if there are changes to the indicies!
# https://docs.tzpro.io/api/index/tables/income-table

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
idx_n_baking_rights = 8
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


def load_key_from_env_variables():
    load_dotenv()
    try:
        key = os.getenv("TZPRO_API_KEY")
    except:
        verbose_logger.exception("Unable to load TZPRO_API_KEY from .env file!")
    if key == "":
        verbose_logger.exception(
            "Please copy the .env.example file to .env and add your personal TZPRO_API_KEY!"
        )
    return key
