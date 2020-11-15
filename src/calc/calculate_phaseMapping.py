from calc.calculate_phase_base import CalculatePhaseBase


class CalculatePhaseMapping(CalculatePhaseBase):
    """
    -- Mapping Phase --

    Set pymntaddress for each payment. By default, address and payment address have the same value.
    Some delegators may request payments to be done to a different address. Payment address change is done at this phase.
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, reward_logs, addr_dest_dict):
        # if address is in address destination dictionary;
        # then set payment address to mapped address value
        for rl in self.filterskipped(reward_logs):
            rl.ratio5 = rl.ratio

            if rl.address in addr_dest_dict:
                rl.paymentaddress = addr_dest_dict[rl.address]

        return reward_logs
