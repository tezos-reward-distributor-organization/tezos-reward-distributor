from log_config import main_logger
from model import reward_log
from calc.calculate_phase_base import CalculatePhaseBase, BY_ZERO_BALANCE

logger = main_logger


class CalculatePhase7(CalculatePhaseBase):
    """
    -- Phase7 : Check if current delegator balance is 0 --

    At stage 7, check each delegate's current balance. If 0, and baker is not reactivating,
    then mark payment as not-payable
    """

    def __init__(self, reactivate_zeroed) -> None:
        super().__init__()
        self.reactivate_zeroed = reactivate_zeroed
        self.phase = 7

    def calculate(self, reward_logs):

        reward_data7 = []

        for delegate in reward_logs:

            # If delegate's current balance is 0, and we are NOT reactivating it,
            # then mark address as being skipped with a description to be included
            # in the database payment report

            # KT1 accounts do not require reactivation on 0 balance

            if (delegate.type == reward_log.TYPE_DELEGATOR
                    and delegate.current_balance == 0
                    and not delegate.paymentaddress.startswith("KT1")):

                if self.reactivate_zeroed:
                    delegate.needs_activation = True
                else:
                    delegate.skip(BY_ZERO_BALANCE, self.phase)

            reward_data7.append(delegate)

        return reward_data7
