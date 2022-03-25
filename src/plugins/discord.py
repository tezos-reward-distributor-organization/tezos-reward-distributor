import logging

from Constants import MUTEZ_PER_TEZ
from plugins import plugins

# Plugin specific libs
import requests

logger = logging.getLogger("main.plugins.discord")

plugin_name = "DiscordPlugin"


class DiscordPlugin(plugins.Plugin):

    _req_cfg_keys = ["endpoint", "discord_text", "send_admin"]

    def __init__(self, cfg):
        super().__init__("Discord", cfg["discord"])
        logger.info("[DiscordPlugin] WebHook URL: {:s}".format(self.endpoint))

    def send_admin_notification(
        self, subject, message, attachments=None, reward_data=None
    ):

        admin_text = "**{:s}**\n{:s}".format(subject, message)
        if self.send_admin:
            self.post_to_discord(admin_text, "ADMIN")

    def send_payout_notification(self, cycle, payout_amount, nb_delegators):

        # Do template replacements
        payout_message = (
            self.discord_text.replace("%CYCLE%", str(cycle))
            .replace("%TREWARDS%", str(round(payout_amount / MUTEZ_PER_TEZ, 2)))
            .replace("%NDELEGATORS%", str(nb_delegators))
        )
        self.post_to_discord(payout_message, "PAYOUT")

    def post_to_discord(self, message, type):

        try:
            resp = requests.post(
                self.endpoint,
                json={"content": message},
                timeout=15,
                headers={"user-agent": "trd/8.0"},
            )
        except requests.exceptions.RequestException as e:
            logger.error("[DiscordPlugin] {:s} Error '{:s}'".format(type, str(e)))
            return

        # else, no error
        logger.info(
            "[DiscordPlugin] {:s} Notification sent; Response {:d} {:s}".format(
                type, resp.status_code, resp.text
            )
        )

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
        self.discord_text = self.cfg["discord_text"]
        self.send_admin = self.cfg["send_admin"]

        # Sanity
        if self.endpoint is None:
            raise plugins.PluginConfigurationError(
                "[{:s}] Not Configured".format(self.name)
            )

        if len(self.discord_text) < 10:
            raise plugins.PluginConfigurationError(
                "[{:s}] 'discord_text' must be longer than 10 characters".format(
                    self.name
                )
            )
