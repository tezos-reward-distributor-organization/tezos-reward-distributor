from functools import reduce

from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT, TYPE_OWNERS_PARENT, TYPE_MERGED
from util.rounding_command import RoundingCommand

MUTEZ = 1e+6


class CalculatePhase5(CalculatePhaseBase):
    """
    At stage 5, merge payments.
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, reward_data4, total_amount):
        skipped_rewards = list(self.iterateskipped(reward_data4))
        rewards = list(self.filterskipped(reward_data4))

        # create a dictionary of address and reward logs
        # an address may be mapped to one more than once reward log
        address_set = set([rl.address for rl in rewards])
        address_rewards_dict = {address: [] for address in address_set}
        for rl in rewards:
            address_rewards_dict[rl.address].append(rl)

        # generate new rewards, rewards with the same address are merged
        new_rewards = [RewardLog.RewardLog5(addr, type=TYPE_MERGED if len(address_rewards_dict[addr])>1 else address_rewards_dict[addr][0].type,
                                            ratio5=sum([rl4.ratio4 for rl4 in address_rewards_dict[addr]]))
                       for addr in address_set]

        # add skipped rewards
        new_rewards.extend(skipped_rewards)

        return new_rewards, total_amount
