import logging

from log_config import verbose_logger
from plugins import plugins

# Plugin specific libs
import requests

logger = logging.getLogger("main.plugins.telegram")

plugin_name = 'TelegramPlugin'


class TelegramPlugin(plugins.Plugin):

    _req_cfg_keys = ["chat_ids", "bot_api_key"]
    _base_api_url = "https://api.telegram.org/bot{:s}/sendMessage"

    def __init__(self, cfg):
        super().__init__("Telegram", cfg["telegram"])
        self.api_url = self._base_api_url.format(self.bot_api_key)

    def send_notification(self, title, message, attachments=None, reward_data=None):

        # Add sparkles emoji to message
        message = "&#x2728; <b>{:s}</b>\n{:s}".format(title, message)

        for c in self.chat_ids:
            payload = {"chat_id": c, "parse_mode": "html", "text": message}
            resp = requests.post(self.api_url, params=payload)

        verbose_logger.debug("[TelegramPlugin] Response: {:}".format(resp.json()))

        logger.info("[TelegramPlugin] Notification '{:s}' sent".format(title))

    def validateConfig(self):
        """Check that that passed config contains all the necessary
           parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError("[{:s}] '{:s}' setting not found".format(self.name, k))

        # Set config
        self.chat_ids = self.cfg["chat_ids"]
        self.bot_api_key = self.cfg["bot_api_key"]

        # Sanity
        if self.chat_ids is None or self.bot_api_key is None:
            raise plugins.PluginConfigurationError("[{:s}] Not Configured".format(self.name))

        # ChatIds must be a list
        if not isinstance(self.chat_ids, list):
            raise plugins.PluginConfigurationError("[{:s}] 'chat_ids' must be in list format".format(self.name))
