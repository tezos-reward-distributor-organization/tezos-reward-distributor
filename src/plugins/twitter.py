import logging
from plugins import plugins

# Plugin specific libs
import tweepy

logger = logging.getLogger("main.plugins.twitter")

plugin_name = 'TwitterPlugin'


class TwitterPlugin(plugins.Plugin):
    MAX_TWEET_LEN = 280

    _req_cfg_keys = ["api_key", "api_secret", "access_token", "access_secret"]
    _base_api_url = "https://api.twitter.com/1.1/statuses/update.json"

    def __init__(self, cfg):
        super().__init__("Twitter", cfg["twitter"])

        # Must auth against Twitter API to get Token
        auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
        auth.set_access_token(self.access_token, self.access_secret)

        self.twitter = tweepy.API(auth)

        # If the authentication was successful, you should
        # see the name of the account print out
        logger.info("[TwitterPlugin] Authenticated '{:s}'".format(self.twitter.me().name))

    def send_notification(self, title, message, attachments=None, reward_data=None):

        # Merge title and message to form tweet
        tweet = "{:s} {:s}".format(title, message)

        # Join hashtags together
        hash_tags = ""
        if self.extra_tags is not None:
            hash_tags = " ".join(self.extra_tags)

        # Tags are important for those that follow bakers' messages.
        # Truncate message before adding tags.
        tweet = tweet[:(self.MAX_TWEET_LEN - len(hash_tags) - 1)]
        message = "{:s} {:s}".format(tweet, hash_tags)

        resp = self.twitter.update_status(message)
        logger.info("[TwitterPlugin] Notification '{:s}' sent".format(title))
        logger.debug("[TwitterPlugin] Response '{:s}'".format(str(resp)))

    def validateConfig(self):
        """Check that that passed config contains all the necessary
           parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError("[{:s}] '{:s}' setting not found".format(self.name, k))

        # Set config
        self.api_key = self.cfg["api_key"]
        self.api_secret = self.cfg["api_secret"]
        self.access_token = self.cfg["access_token"]
        self.access_secret = self.cfg["access_secret"]
        self.extra_tags = self.cfg["extra_tags"]

        # Sanity
        if self.api_key is None or self.api_secret is None or self.access_token is None or self.access_secret is None:
            raise plugins.PluginConfigurationError("[{:s}] Not Configured".format(self.name))

        if self.extra_tags is None:
            logger.info("[TwitterPlugin] No hashtags defined; Just letting you know")

        elif self.extra_tags is not None and not isinstance(self.extra_tags, list):
            raise plugins.PluginConfigurationError("[{:s}] 'extra_tags' not configured correctly".format(self.name))
