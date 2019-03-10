import functools

from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import RewardLog, cmp

MUTEZ = 1e+6


class CalculatePhase5(CalculatePhaseBase):
    """
    -- Phase5 : Merge Phase --

    At stage 5, merge payments.
    Set pymntaddress for each payment. By default, address and payment address have the same value.
    Some delegators may request payments to be done to a different address. Payment address change is done at this phase.
    Payments to the same destination are merged.
    """

    def __init__(self, addr_dest_dict) -> None:
        super().__init__()
        self.addr_dest_dict = addr_dest_dict

    def calculate(self, reward_data4, total_amount):
        skipped_rewards = list(self.iterateskipped(reward_data4))
        rewards = list(self.filterskipped(reward_data4))

        # if address is in address destination dictionary;
        # then set payment address to mapped address value
        for rl4 in rewards:
            if rl4.address in self.addr_dest_dict:
                rl4.pymntaddress = self.addr_dest_dict[rl4.address]

        # create a dictionary of address and reward logs
        # an address may be mapped to one more than once reward log
        pymnt_address_set = set([rl.pymntaddress for rl in rewards])
        address_rewards_dict = {paddress: [] for paddress in pymnt_address_set}
        for rl in rewards:
            address_rewards_dict[rl.pymntaddress].append(rl)

        # generate new rewards, rewards with the same address are merged
        new_rewards = []
        for paddr in pymnt_address_set:
            if len(address_rewards_dict[paddr]) > 1:
                rl5 = RewardLog.RewardLog5(paddr, address_rewards_dict[paddr])
                new_rewards.append(rl5)
            elif len(address_rewards_dict[paddr]) == 1:
                rl5 = address_rewards_dict[paddr][0]
                rl5.ratio5 = rl5.ratio4
                new_rewards.append(rl5)
            else:
                raise Exception(
                    "length of address_rewards_dict[addr] cannot be 1. Report this issue. Addr={}".format(paddr))

        # add skipped rewards
        new_rewards.extend(skipped_rewards)

        new_rewards.sort(key=functools.cmp_to_key(cmp))

        return new_rewards, total_amount
