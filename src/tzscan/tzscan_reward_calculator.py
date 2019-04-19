from api.reward_calculator_api import RewardCalculatorApi
from model.payment_log import PaymentRecord
from log_config import main_logger
from tzscan.tzscan_reward_api import TzScanRewardApiImpl
from util.rounding_command import RoundingCommand

MUTEZ = 1000000


class TzScanRewardCalculatorApi(RewardCalculatorApi):
    # reward_data : payment map returned from tzscan
    def __init__(self, founders_map, min_delegation_amt, excluded_set, rc=RoundingCommand(None)):
        super(TzScanRewardCalculatorApi, self).__init__(founders_map, excluded_set)
        self.min_delegation_amt_mutez = min_delegation_amt * MUTEZ
        self.logger = main_logger
        self.rc = rc

    ##
    # return rewards    : tuple (list of PaymentRecord objects, total rewards)
    def calculate(self, reward_data):
        root = reward_data

        delegate_staking_balance = int(root["delegate_staking_balance"])
        blocks_rewards = int(root["blocks_rewards"])
        future_blocks_rewards = int(root["future_blocks_rewards"])
        endorsements_rewards = int(root["endorsements_rewards"])
        future_endorsements_rewards = int(root["future_endorsements_rewards"])
        lost_rewards_denounciation = int(root["lost_rewards_denounciation"])
        lost_fees_denounciation = int(root["lost_fees_denounciation"])
        fees = int(root["fees"])

        self.total_rewards = (blocks_rewards + endorsements_rewards + future_blocks_rewards +
                              future_endorsements_rewards + fees - lost_rewards_denounciation - lost_fees_denounciation) / MUTEZ

        delegators_balance = root["delegators_balance"]

        effective_delegate_staking_balance = delegate_staking_balance
        effective_delegators_balance = []

        # excluded addresses are processed
        for dbalance in delegators_balance:
            address = dbalance[0]["tz"]
            balance = int(dbalance[1])

            if address in self.excluded_set:
                effective_delegate_staking_balance -= balance
                continue
            effective_delegators_balance.append(dbalance)

        rewards = []
        # calculate how rewards will be distributed
        for dbalance in effective_delegators_balance:
            address = dbalance[0]["tz"]
            balance = int(dbalance[1])

            # Skip those that did not delegate minimum amount
            if balance < self.min_delegation_amt_mutez:
                self.logger.debug("Skipping '{}': Low delegation amount ({:.6f})".format(address, (balance / MUTEZ)))
                continue

            ratio = self.rc.round(balance / effective_delegate_staking_balance)
            reward = (self.total_rewards * ratio)

            reward_item = PaymentRecord(address=address, reward=reward, ratio=ratio)

            rewards.append(reward_item)

        return rewards, self.total_rewards


def test_tzscan_reward_calculator():
    tzScanRewardApi = TzScanRewardApiImpl(
        {'NAME': 'ZERONET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 20, 'BLOCKS_PER_CYCLE': 128},
        "tz1YRewYxRtxk57gTbaj5wANdSRmhwEf77Bz")
    reward_list = tzScanRewardApi.get_rewards_for_cycle_map(250)

    tzscanRewardCalculator = TzScanRewardCalculatorApi(set(), reward_list, 0, set())
    rewards, total_rewards = tzscanRewardCalculator.calculate()
    i = 0
    reward_sum = 0
    ratio_sum_before = 0
    for reward in rewards:
        i += 1

        print(i, reward)

        reward_sum += reward.reward
        ratio_sum_before += reward.ratio

    print("n_rewards {}".format(len(rewards)))

    if reward_sum != total_rewards:
        raise Exception("Reward Sum={} but expected {}".format(reward_sum, total_rewards))

    excluded_set = {"KT18e4LRVsRPthhvnaqQ8QH9gEoc45reNDhj", "KT192bqLuUos2HtPRK8jp4yL9gaXLyBsz7pL",
                    "KT19cVk1ZWg217GK55uB8JqPqxWp41dXMTiB", "KT19GF1HkPDNvrQehkGy8om3qaPwkXxjTGaY",
                    "KT1AAZ5URdDfeunZoTxXLHBZQ8H9h8rynVNF", "KT1At5hxVamL5Q6r7Y3ijW3e1QRQgBbrFxZH",
                    "KT1BoGLM6KuRYRaFj3fs2Njsn9roPaCohgaY", "KT1BpPHFtPKC6mkhchFs5FV37oFefCrfeYQA",
                    "KT1Ax8HHLcNGAaxzrXK8Sigx1xoreLkutv3R", "KT1AxuU1bXPixmFmkpu8KvEY7RL7wB7mADtG"}
    tzscanRewardCalculator = TzScanRewardCalculatorApi(set(), reward_list, excluded_set)
    rewards, total_rewards = tzscanRewardCalculator.calculate()

    i = 0
    reward_sum = 0
    ratio_sum_after = 0
    for reward in rewards:
        i += 1

        print(i, reward)

        reward_sum += reward.reward
        ratio_sum_after += reward.ratio

    print("n_rewards {}".format(len(rewards)))

    if reward_sum != total_rewards:
        raise Exception("Reward Sum={} but expected {}".format(reward_sum, total_rewards))

    if ratio_sum_after >= ratio_sum_before:
        raise Exception(
            "ratio_sum_after {} must be greater than ratio_sum_before {}".format(ratio_sum_after, ratio_sum_before))

    # if ratio_sum != 1:
    #    raise Exception("Ratio Sum={} but expected {}".format(ratio_sum, 1))
