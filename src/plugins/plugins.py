import importlib
import logging
from os import path, rename

logger = logging.getLogger("main.plugins")

EMAIL_INI_PATH = "./email.ini"


# Manager class for the plugin subsystem
class PluginManager(object):

    def __init__(self, cfg, verbose=False, dry_run=False):
        self.plugins = []
        self.verbose = verbose
        self.dry_run = dry_run

        # Temporary message to notify of upgrade. Should be removed on next release.
        # Look for older email.ini file and print notice of upgrade
        if path.isfile(EMAIL_INI_PATH):
            logger.warning("[Plugins] Detected obselete email config file. Please convert to the new plugins system. 'email.ini' renamed 'email.ini.old'")
            rename(EMAIL_INI_PATH, "{:s}.old".format(EMAIL_INI_PATH))

        # Get the list of enabled plugins, and attempt to load
        if cfg["enabled"] is not None:

            if not isinstance(cfg["enabled"], list):
                raise PluginConfigurationError("[Plugins] 'enabled' list is not properly configured.")

            for p in cfg["enabled"]:
                self.loadPlugin(p, cfg)

        # Print notice if no plugins loaded/enabled
        if not self.plugins:
            logger.info("[Plugins] No plugins enabled")

    # Go through each plugin module and call send_notification
    def send_notification(self, subject, message, attachments=None, reward_data=None):

        if not self.plugins:
            logger.info("[Plugins] Not sending notification; no plugins enabled")

        for p in self.plugins:
            if not self.dry_run:
                try:
                    p.send_notification(subject, message, attachments, reward_data)
                except Exception as e:
                    logger.error("[Plugins] [{:s}] Unknown Error: {:s}".format(p.name, str(e)))
            else:
                logger.info("[Plugins] [{:s}] send_notification (Dry-Run mode)".format(p.name))

    # Dynamically load python modules as plugins
    def loadPlugin(self, plugin_name, cfg):

        try:
            # Dynamically load the .py file for the plugin
            imported_plugin = importlib.import_module("plugins." + plugin_name)

            # Get the class name of the plugin from the module variable
            plugin_ = getattr(imported_plugin, imported_plugin.plugin_name)

            # Create instance of plugin, dynamically, passing config object
            # config object should be parsed/validated by each plugin and
            # plugin should throw PluginConfigurationError if config is invalid
            plugin = plugin_(cfg, self.verbose)

            # Add plugin instance to manager
            self.plugins.append(plugin)

            logger.info("[Plugins] Loaded plugin {:s}".format(plugin.name))

        except ModuleNotFoundError as pe:
            logger.error("[Plugins] Unable to load plugin '{:s}': {:s}. Please check documentation.".format(plugin_name, str(pe)))
        except PluginConfigurationError as pe:
            logger.error("[Plugins] Unable to load plugin: {:s}".format(str(pe)))


# Base class from which all plugins should sub-class
class Plugin(object):
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg
        self.validateConfig()

    def send_notification(self, subject, message, attachments, reward_data):
        raise NotImplementedError

    def validateConfig(self):
        raise NotImplementedError


class PluginConfigurationError(Exception):
    pass
