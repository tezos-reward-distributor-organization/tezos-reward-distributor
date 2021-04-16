import copy
from src.Constants import PaymentStatus
from src.plugins.webhook import WebhookPlugin
from src.model.reward_log import RewardLog


# Default rewardlog
rewardlog = RewardLog(
    "tz1LrHNbbCLgNJZsEsTUYFvWz2THgJC8fHyX",
    "D",
    staking_balance=65116664916,
    current_balance=100000000000,
)
rewardlog.cycle = 415
rewardlog.ratio = 0.16080255
rewardlog.service_fee_ratio = 0.01398283
rewardlog.amount = 207756875
rewardlog.service_fee_amount = 18065815
rewardlog.service_fee_rate = 0.08
rewardlog.payable = True
rewardlog.skipped = False
rewardlog.hash = "oo4Gikxyj8cMqM8xzgWxqnsxXoGwfhZqHDrLqpA6ENmMVoYUnVd"
rewardlog.neededActivation = False
rewardlog.paid = PaymentStatus.DONE

# Second reward log with floats
rewardlog2 = copy.deepcopy(rewardlog)
rewardlog2.staking_balance = 123123123.0
rewardlog2.current_balance = 1000000000.0
rewardlog2.amount = 200066666.0
rewardlog2.service_fee_amount = 789789789.0

# Third reward log with strings
rewardlog3 = copy.deepcopy(rewardlog)
rewardlog3.staking_balance = "98765643"
rewardlog2.current_balance = "1000000000"
rewardlog3.amount = "12345678900"
rewardlog3.service_fee_amount = "5555555"
rewardlog3.ratio = "0.16080255"
rewardlog3.service_fee_ratio = "0.01398283"
rewardlog3.service_fee_rate = "0.08"

cfg = {
    "webhook": {
        "endpoint": "https://testnet-tezos.giganode.io:443",
        "token": "Xynl6svphysd3BhjLP6IS",
    }
}


def test_webhook_payload_types():
    """
    Test the type correctness of the generated payload
    Issue: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/417
    """
    webhook_plugin = WebhookPlugin(cfg)
    payload = webhook_plugin.generate_payload(
        "Payouts of cycle 22 completed",
        "Much longer message example containing more information message",
        [rewardlog, rewardlog2, rewardlog3],
    )

    # Check types and values
    stakingBalances = [65116664916, 123123123, 98765643]
    amounts = [207756875, 200066666, 12345678900]
    feeAmounts = [18065815, 789789789, 5555555]
    for index, payout in enumerate(payload["payouts"]):
        assert isinstance(payout["stakingBalance"], int)
        assert payout["stakingBalance"] == stakingBalances[index]

        assert isinstance(payout["amount"], int)
        assert payout["amount"] == amounts[index]

        assert isinstance(payout["feeAmount"], int)
        assert payout["feeAmount"] == feeAmounts[index]
