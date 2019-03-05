class RewardProviderModel:
    def __init__(self, delegate_staking_balance, total_reward_amount, delegator_balance_dict) -> None:
        super().__init__()
        self.delegator_balance_dict = delegator_balance_dict
        self.total_reward_amount = total_reward_amount
        self.delegate_staking_balance = delegate_staking_balance