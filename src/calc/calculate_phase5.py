from calc.calculate_phase_base import CalculatePhaseBase


class CalculatePhase5(CalculatePhaseBase):
    """
    -- Phase5 : Mapping Phase --

    At stage 5, map payments.
    Set pymntaddress for each payment. By default, address and payment address have the same value.
    Some delegators may request payments to be done to a different address. Payment address change is done at this phase.
    """

    def __init__(self, addr_dest_dict) -> None:
        super().__init__()
        self.addr_dest_dict = addr_dest_dict

    def calculate(self, reward_data4, total_amount):
        # if address is in address destination dictionary;
        # then set payment address to mapped address value
        for rl in self.filterskipped(reward_data4):
            rl.ratio5 = rl.ratio

            if rl.address in self.addr_dest_dict:
                rl.paymentaddress = self.addr_dest_dict[rl.address]

        return reward_data4, total_amount
