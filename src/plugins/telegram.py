import logging

from log_config import verbose_logger
from plugins import plugins

# Plugin specific libs
import requests

logger = logging.getLogger("main.plugins.telegram")
MUTEZ = 1e6

plugin_name = 'TelegramPlugin'


class TelegramPlugin(plugins.Plugin):

    _req_cfg_keys = ["admin_chat_ids", "payouts_chat_ids", "bot_api_key", "telegram_text"]
    _base_api_url = "https://api.telegram.org/bot{:s}/sendMessage"

    def __init__(self, cfg):
        super().__init__("Telegram", cfg["telegram"])
        self.api_url = self._base_api_url.format(self.bot_api_key)

    def send_admin_notification(self, subject, message, attachments=None, reward_data=None):

        admin_text = "<b>{:s}</b>\n{:s}".format(subject, message)

        for c in self.admin_chat_ids:
            payload = {"chat_id": c, "parse_mode": "html", "text": admin_text}
            resp = requests.post(self.api_url, params=payload)

        verbose_logger.debug("[TelegramPlugin] Admin Response: {:}".format(resp.json()))

        logger.info("[TelegramPlugin] Admin Notification '{:s}' sent".format(subject))

    def send_payout_notification(self, cycle, payout_amount, nb_delegators):

        # Add sparkles emoji to message
        message = self.telegram_text \
            .replace("%CYCLE%", str(cycle)) \
            .replace("%TREWARDS%", str(round(payout_amount / MUTEZ, 2))) \
            .replace("%NDELEGATORS%", str(nb_delegators))

        for c in self.payouts_chat_ids:
            payload = {"chat_id": c, "parse_mode": "html", "text": message}
            resp = requests.post(self.api_url, params=payload)

        verbose_logger.debug("[TelegramPlugin] Public Response: {:}".format(resp.json()))

        logger.info("[TelegramPlugin] Public Notification '{:s}...' sent".format(message[:20]))

    def validateConfig(self):
        """Check that that passed config contains all the necessary
           parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        # Upgrade notification
        if "chat_ids" in cfg_keys:
            raise plugins.PluginConfigurationError("[{:s}] 'chat_ids' no longer supported; Please see upgrading instructions.".format(self.name))

        # Check for required config parameters
        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError("[{:s}] '{:s}' setting not found".format(self.name, k))

        # Set config
        self.admin_chat_ids = self.cfg["admin_chat_ids"]
        self.payouts_chat_ids = self.cfg["payouts_chat_ids"]
        self.bot_api_key = self.cfg["bot_api_key"]
        self.telegram_text = self.cfg["telegram_text"]

        # Sanity; Admin chat ids required at minimum
        if self.admin_chat_ids is None or self.bot_api_key is None:
            raise plugins.PluginConfigurationError("[{:s}] Not Configured".format(self.name))

        # adminChatIds must be a list
        if not isinstance(self.admin_chat_ids, list):
            raise plugins.PluginConfigurationError("[{:s}] 'admin_chat_ids' must be in list format".format(self.name))

        # Same for publicChatIds
        if not isinstance(self.payouts_chat_ids, list):
            raise plugins.PluginConfigurationError("[{:s}] 'payouts_chat_ids' must be in list format".format(self.name))

        # Text must be longer than 10 characters
        if len(self.telegram_text) < 10:
            raise plugins.PluginConfigurationError("[{:s}] 'telegram_text' must longer than 10 characters".format(self.name))
