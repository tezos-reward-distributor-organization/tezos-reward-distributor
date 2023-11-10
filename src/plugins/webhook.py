import logging
from plugins import plugins

# Plugin specific libs
import requests
from time import time

logger = logging.getLogger("main.plugins.webhook")

plugin_name = "WebhookPlugin"


class WebhookPlugin(plugins.Plugin):
    _req_cfg_keys = ["endpoint", "token"]

    def __init__(self, cfg):
        super().__init__("Webhook", cfg["webhook"])

        logger.info("[WebhookPlugin] Endpoint: {:s}".format(self.endpoint))

    def generate_payload(self, subject, message, rewards):
        # Create JSON object to be POST'd to hook URL
        payload = {
            "timestamp": int(time()),
            "token": self.token,
            "subject": subject,
            "message": message,
            "payouts": [],
        }

        # Loop over rewards (RewardLogs) and append
        for reward in rewards:
            reward = self.cast(reward)
            payout = {
                "address": reward.address,
                "paymentAddress": reward.paymentaddress,
                "addressType": reward.type,
                "cycle": reward.cycle,
                "stakingBalance": reward.staking_balance,
                "ratio": reward.ratio,
                "feeRatio": reward.service_fee_ratio,
                "adjustedAmount": reward.adjusted_amount,
                "feeAmount": reward.service_fee_amount,
                "feeRate": reward.service_fee_rate,
                "payable": reward.payable,
                "skipped": reward.skipped,
                "opHash": reward.hash,
                "neededActivation": reward.needs_activation,
                "paymentStatus": reward.paid.name,
            }
            payload["payouts"].append(payout)
        return payload

    def send_admin_notification(
        self, subject, message, attachments=None, reward_data=None
    ):
        payload = self.generate_payload(subject, message, reward_data)

        try:
            resp = requests.post(
                self.endpoint,
                json=payload,
                timeout=15,
                headers={"user-agent": "trd/0.0.1"},
            )
        except requests.exceptions.RequestException as e:
            logger.error("[WebhookPlugin] Error POSTing '{:s}'".format(str(e)))
            return

        # Will log 200, 203, 404, 500, etc
        logger.info(
            "[WebhookPlugin] Notification '{:s}' sent; Response {:d} {:s}".format(
                subject, resp.status_code, resp.text
            )
        )

    def send_payout_notification(self, cycle, payout_amount, nb_delegators):
        logger.error("[WebhookPlugin] Payout notification not implemented yet!")
        return

    def cast(self, reward):
        """Explicit casting of reward log elements."""
        reward.address = str(reward.address)
        reward.paymentaddress = str(reward.paymentaddress)
        reward.type = str(reward.type)
        reward.cycle = int(reward.cycle)
        reward.staking_balance = int(reward.staking_balance)
        reward.ratio = round(float(reward.ratio), 8)
        reward.service_fee_ratio = round(float(reward.service_fee_ratio), 8)
        reward.adjusted_amount = int(reward.adjusted_amount)
        reward.service_fee_amount = int(reward.service_fee_amount)
        reward.service_fee_rate = float(reward.service_fee_rate)
        reward.payable = bool(reward.payable)
        reward.skipped = bool(reward.skipped)
        reward.hash = str(reward.hash)
        reward.needs_activation = bool(reward.needs_activation)
        return reward

    def validateConfig(self):
        """Check that that passed config contains all the necessary
        parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError(
                    "[{:s}] '{:s}' setting not found".format(self.name, k)
                )

        # Set config
        self.endpoint = self.cfg["endpoint"]
        self.token = self.cfg["token"]

        # Sanity
        if self.endpoint is None or self.token is None:
            raise plugins.PluginConfigurationError(
                "[{:s}] Not Configured".format(self.name)
            )
