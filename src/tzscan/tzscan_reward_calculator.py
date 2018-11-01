from api.reward_calculator_api import RewardCalculatorApi

ONE_MILLION = 1000000


class TzScanRewardCalculatorApi(RewardCalculatorApi):
    # reward_data : payment map returned from tzscan
    def __init__(self, founders_map, reward_data):
        super().__init__(founders_map)
        self.reward_data = reward_data

    ##
    # return rewards    : list of reward items ({"address":address, "reward":reward})
    def calculate(self):
        root = self.reward_data

        delegate_staking_balance = int(root["delegate_staking_balance"])
        blocks_rewards = int(root["blocks_rewards"])
        future_blocks_rewards = int(root["future_blocks_rewards"])
        endorsements_rewards = int(root["endorsements_rewards"])
        future_endorsements_rewards = int(root["future_endorsements_rewards"])
        fees = int(root["fees"])

        self.total_rewards = (blocks_rewards + endorsements_rewards + future_blocks_rewards +
                              future_endorsements_rewards + fees) / ONE_MILLION

        delegators_balance = root["delegators_balance"]

        rewards = []
        for dbalance in delegators_balance:
            address = dbalance[0]["tz"]
            balance = int(dbalance[1])
            ratio = round(balance / delegate_staking_balance, 5)
            reward = (self.total_rewards * ratio)
            reward_item = {"address": address, "reward": reward, "ratio": ratio}

            rewards.append(reward_item)

        return rewards
