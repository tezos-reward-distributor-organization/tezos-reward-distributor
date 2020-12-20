from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import RewardLog, TYPE_MERGED


class CalculatePhaseMerge(CalculatePhaseBase):
    """
    -- Merge Phase --

    Payments to the same destination are merged.
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, reward_logs):
        # if address is in address destination dictionary;
        # then set payment address to mapped address value
        for rl in self.filterskipped(reward_logs):
            rl.ratio6 = rl.ratio

        address_set = set(rl.paymentaddress for rl in self.filterskipped(reward_logs))
        payment_address_list_dict = {addr: [] for addr in address_set}

        # group payments by paymentaddress
        for rl in self.filterskipped(reward_logs):
            payment_address_list_dict[rl.paymentaddress].append(rl)

        reward_data6 = []
        for rl in self.iterateskipped(reward_logs):
            reward_data6.append(rl)

        for addr, rl_list in payment_address_list_dict.items():
            if len(rl_list) > 1:
                total_staking_balance = sum([rl.staking_balance for rl in rl_list])
                total_current_balance = sum([rl.current_balance for rl in rl_list])
                total_ratio = sum([rl.ratio for rl in rl_list])
                total_payment_amount = sum([rl.amount for rl in rl_list])
                total_service_fee_amount = sum([rl.service_fee_amount for rl in rl_list])
                total_service_fee_ratio = sum([rl.service_fee_ratio for rl in rl_list])

                merged = RewardLog(addr, TYPE_MERGED, total_staking_balance, total_current_balance)
                merged.ratio = total_ratio
                merged.amount = total_payment_amount
                merged.service_fee_amount = total_service_fee_amount
                merged.service_fee_ratio = total_service_fee_ratio
                merged.service_fee_rate = 0
                merged.parents = rl_list

                reward_data6.append(merged)
            else:
                reward_data6.append(rl_list[0])

        return reward_data6
