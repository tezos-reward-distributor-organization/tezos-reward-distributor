import logging
from plugins import plugins
from Constants import MUTEZ_PER_TEZ

# Plugin specific libs
import tweepy

logger = logging.getLogger("main.plugins.twitter")

plugin_name = "TwitterPlugin"


class TwitterPlugin(plugins.Plugin):

    MAX_TWEET_LEN = 280

    _req_cfg_keys = [
        "api_key",
        "api_secret",
        "access_token",
        "access_secret",
        "tweet_text",
    ]
    _base_api_url = "https://api.twitter.com/1.1/statuses/update.json"

    def __init__(self, cfg):
        super().__init__("Twitter", cfg["twitter"])

        # Must auth against Twitter API to get Token
        auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, self.access_token, self.access_secret)
        self.twitter = tweepy.API(auth)
        version = tweepy.__version__.split(".")
        # tweepy version 4 broke lots of compatibilty, we need to separate from v3
        majorversion = int(version[0])
        # warn on older version than v4
        if majorversion < 4:
            logger.info(
                "Older version of tweetpy please update]"
            )
        logger.info(
            "[TwitterPlugin] Authenticated '{:s}'".format(
                self.twitter.verify_credentials().name
            )
        )

    def send_admin_notification(
        self, title, message, attachments=None, reward_data=None
    ):
        logger.debug("[TwitterPlugin] Admin notifications not implemented")
        return

    def send_payout_notification(self, cycle, payout_amount, nb_delegators):

        # Replace template variables
        tweet = (
            self.tweet_text.replace("%CYCLE%", str(cycle))
            .replace("%TREWARDS%", str(round(payout_amount / MUTEZ_PER_TEZ, 2)))
            .replace("%NDELEGATORS%", str(nb_delegators))
        )

        # Truncate message to max tweet length
        tweet = tweet[: self.MAX_TWEET_LEN]

        resp = self.twitter.update_status(tweet)

        logger.info("[TwitterPlugin] Payout Notification '{:s}' sent".format(tweet))
        logger.debug("[TwitterPlugin] Payout Response '{:s}'".format(str(resp)))

    def validateConfig(self):
        """Check that that passed config contains all the necessary
        parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError(
                    "[TwitterPlugin] '{:s}' setting not found; Please read documentation".format(
                        k
                    )
                )

        # Set config
        self.api_key = self.cfg["api_key"]
        self.api_secret = self.cfg["api_secret"]
        self.access_token = self.cfg["access_token"]
        self.access_secret = self.cfg["access_secret"]
        self.tweet_text = self.cfg["tweet_text"]

        # Sanity
        if (
            self.api_key is None
            or self.api_secret is None
            or self.access_token is None
            or self.access_secret is None
        ):
            raise plugins.PluginConfigurationError(
                "[TwitterPlugin] Missing required parameters; Please read documentation"
            )

        if self.tweet_text is None:
            raise plugins.PluginConfigurationError(
                "[TwitterPlugin] No tweet text defined; Please read documentation"
            )
