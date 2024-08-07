class RewardProviderModel:
    def __init__(
        self,
        own_delegated_balance,
        external_delegated_balance,
        num_baking_rights,
        potential_endorsement_rewards,
        total_reward_amount,
        rewards_and_fees,
        equivocation_losses,
        denunciation_rewards,
        offline_losses,
        delegator_balance_dict,
        computed_reward_amount,
    ) -> None:
        super().__init__()
        self.delegator_balance_dict = delegator_balance_dict
        self.own_delegated_balance = own_delegated_balance
        self.external_delegated_balance = external_delegated_balance
        self.num_baking_rights = num_baking_rights

        # endorsement rewards, if paid, will equal this amount
        self.potential_endorsement_rewards = potential_endorsement_rewards

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
