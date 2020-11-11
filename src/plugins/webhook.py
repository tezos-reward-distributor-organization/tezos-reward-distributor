import logging
from plugins import plugins

# Plugin specific libs
import requests
from time import time

logger = logging.getLogger("main.plugins.webhook")

plugin_name = 'WebhookPlugin'


class WebhookPlugin(plugins.Plugin):

    _req_cfg_keys = ["endpoint", "token"]

    def __init__(self, cfg, verbose=False):
        super().__init__("Webhook", cfg["webhook"])
        self.verbose = verbose

        logger.info("[WebhookPlugin] Endpoint: {:s}".format(self.endpoint))

    def send_notification(self, title, message, attachments=None, reward_data=None):

        # Create JSON object to be POST'd to hook URL
        payload = {"timestamp": int(time()),
                   "token": self.token,
                   "payouts": []
                   }

        # Loop over reward_data (RewardLogs) and append
        for i in reward_data:
            payout = {"address": i.address, "paymentAddress": i.paymentaddress,
                      "addressType": i.type, "cycle": i.cycle, "stakingBalance": i.staking_balance,
                      "ratio": round(i.ratio, 8), "feeRatio": round(i.service_fee_ratio, 8),
                      "amount": i.amount, "feeAmount": i.service_fee_amount, "feeRate": i.service_fee_rate,
                      "payable": i.payable, "skipped": i.skipped, "opHash": i.hash,
                      "neededActivation": i.needs_activation, "paymentStatus": i.paid.name
                      }
            payload["payouts"].append(payout)

        resp = requests.post(self.endpoint, json=payload, timeout=15)

        logger.info("[WebhookPlugin] Notification '{:s}' sent; Response {:d} {:s}"
                    .format(title, resp.status_code, resp.text))

    def validateConfig(self):
        """Check that that passed config contains all the necessary
           parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError("[{:s}] '{:s}' setting not found".format(self.name, k))

        # Set config
        self.endpoint = self.cfg["endpoint"]
        self.token = self.cfg["token"]

        # Sanity
        if self.endpoint is None or self.token is None:
            raise plugins.PluginConfigurationError("[{:s}] Not Configured".format(self.name))
