from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import RewardLog, TYPE_MERGED

MUTEZ = 1e+6


class CalculatePhase6(CalculatePhaseBase):
    """
    -- Phase6 : Merge Phase --

    At stage 6, merge payments.
    Payments to the same destination are merged.
    """

    def __init__(self, addr_dest_dict) -> None:
        super().__init__()
        self.addr_dest_dict = addr_dest_dict

    def calculate(self, reward_data5, total_amount):
        # if address is in address destination dictionary;
        # then set payment address to mapped address value
        for rl in self.filterskipped(reward_data5):
            rl.ratio6 = rl.ratio

        address_set = set(rl.paymentaddress for rl in self.filterskipped(reward_data5))
        payment_address_list_dict = {addr: [] for addr in address_set}
        # group payments by paymentaddress
        for rl in self.filterskipped(reward_data5):
            payment_address_list_dict[rl.paymentaddress].append(rl)

        reward_data6 = []
        for rl in self.iterateskipped(reward_data5):
            reward_data6.append(rl)

        for addr, rl_list in payment_address_list_dict.items():
            if len(rl_list) > 1:
                total_balance = sum([rl.staking_balance for rl in rl_list])
                total_ratio = sum([rl.ratio for rl in rl_list])
                total_payment_amount = sum([rl.amount for rl in rl_list])
                total_service_fee_amount = sum([rl.service_fee_amount for rl in rl_list])
                total_service_fee_ratio = sum([rl.service_fee_ratio for rl in rl_list])

                merged = RewardLog(addr, TYPE_MERGED, total_balance)
                merged.ratio = total_ratio
                merged.amount = total_payment_amount
                merged.service_fee_amount = total_service_fee_amount
                merged.service_fee_ratio = total_service_fee_ratio
                merged.service_fee_rate = 0
                merged.parents = rl_list

                reward_data6.append(merged)
            else:
                reward_data6.append(rl_list[0])

        return reward_data6, total_amount
