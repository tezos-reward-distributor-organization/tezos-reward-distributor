from calc.calculate_phase_base import CalculatePhaseBase
from model import reward_log
from model.reward_log import RewardLog
from util.rounding_command import RoundingCommand

MUTEZ = 1e+6


class CalculatePhase0(CalculatePhaseBase):
    """
    -- Phase0 : Provider Phase --

    Calculate ratios for each delegator based on tz scan data. @see calculate function.
    """

    def __init__(self, reward_provider_model, percent_round_mode=RoundingCommand(None)) -> None:
        """
        Constructor
        :param reward_provider_model: Data from provider
        :param percent_round_mode: RoundingCommand object for percentage calculations. Since this is the first layer in
        calculations RoundingCommand(None) is recommended to avoid rounding.
        """
        super().__init__()

        self.reward_provider_model = reward_provider_model
        self.prcnt_rm = percent_round_mode

    def calculate(self, reward_logs=None, total_reward_amount=None):
        """
        :param reward_logs: Nothing is expected. This value is not used. reward_logs are generated from provider object.
        :param total_reward_amount: Nothing is expected. This value is not used. total amount is taken from provider object.
        :return: tuple (reward_logs, total reward amount)

        reward_logs is a list of RewardLog objects. Last item is owners_parent record.
        total_reward equals to sum( delegator rewards + owners_parent rewards )
        """

        ratio_sum = 0.0
        total_delegator_balance = 0
        reward_logs = []
        delegate_staking_balance = self.reward_provider_model.delegate_staking_balance
        delegators_balance_dict = self.reward_provider_model.delegator_balance_dict
        # calculate how rewards will be distributed
        # ratio is stake/total staking balance
        # total of ratios must be 1
        for address, balance in delegators_balance_dict.items():
            total_delegator_balance += balance

            ratio = self.prcnt_rm.round(balance / delegate_staking_balance)
            reward_item = RewardLog(address=address, type=reward_log.TYPE_DELEGATOR, balance=balance)
            reward_item.ratio = ratio
            reward_item.ratio0 = reward_item.ratio

            ratio_sum += ratio

            reward_logs.append(reward_item)

        owners_rl = RewardLog(address=reward_log.TYPE_OWNERS_PARENT, type=reward_log.TYPE_OWNERS_PARENT,
                              balance=delegate_staking_balance - total_delegator_balance)
        owners_rl.ratio = (1 - ratio_sum)
        owners_rl.ratio0 = owners_rl.ratio

        reward_logs.append(owners_rl)

        return reward_logs, self.reward_provider_model.total_reward_amount
