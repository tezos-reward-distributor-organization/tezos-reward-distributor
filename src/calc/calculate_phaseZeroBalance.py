from log_config import main_logger
from calc.calculate_phase_base import CalculatePhaseBase, BY_ZERO_BALANCE
from model.reward_log import TYPE_DELEGATOR, TYPE_MERGED

logger = main_logger


class CalculatePhaseZeroBalance(CalculatePhaseBase):
    """
    -- Check if current delegator balance is 0 --

    Check each delegator's current balance. If 0, and baker is not reactivating,
    then mark payment as not-payable
    """

    def __init__(self) -> None:
        super().__init__()
        self.phase = 7

    def calculate(self, reward_logs, reactivate_zeroed):

        reward_data7 = []
        for delegate in reward_logs:

            # If delegate's current balance is 0, and we are NOT reactivating it,
            # then mark address as being skipped with a description to be included
            # in the CSV payment report

            # KT1 accounts do not require reactivation on 0 balance
            #
            # Note: This only applies for delegators and merged types
            if (
                delegate.current_balance == 0
                and not delegate.paymentaddress.startswith("KT1")
            ):
                qualified_activation = reactivate_zeroed or not (
                    delegate.type == TYPE_DELEGATOR or delegate.type == TYPE_MERGED
                )
                if qualified_activation:
                    delegate.needs_activation = True
                    logger.info(
                        "{:s} has a 0 balance and will be reactivated".format(
                            delegate.address
                        )
                    )
                else:
                    delegate.skip(BY_ZERO_BALANCE, self.phase)
                    logger.info(
                        "{:s} has a 0 balance and will NOT be reactivated".format(
                            delegate.address
                        )
                    )

            reward_data7.append(delegate)

        return reward_data7
