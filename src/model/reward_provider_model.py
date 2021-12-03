class RewardProviderModel:
    def __init__(self, delegate_staking_balance, num_baking_rights, num_endorsing_rights,
                 total_reward_amount, rewards_and_fees, equivocation_losses, denunciation_rewards,
                 offline_losses, delegator_balance_dict, computed_reward_amount) -> None:
        super().__init__()
        self.delegator_balance_dict = delegator_balance_dict
        self.delegate_staking_balance = delegate_staking_balance
        self.num_baking_rights = num_baking_rights
        self.num_endorsing_rights = num_endorsing_rights
        # rewards that should have been earned, had the baker been online
        self.offline_losses = offline_losses

        # total reward as recorded in-protocol
        self.total_reward_amount = total_reward_amount

        # When using indexers, the total amount above can be itemized as follows:

        # * baking rewards, fees, revelation rewards
        self.rewards_and_fees = rewards_and_fees

        # * losses from double baking/endorsing
        self.equivocation_losses = equivocation_losses

        # * rewards from denunciating other people's double baking/endorsing
        self.denunciation_rewards = denunciation_rewards

        # Computed reward amount - depends on user preferences (expected/actual, pay denunciation etc....)
        self.computed_reward_amount = computed_reward_amount
