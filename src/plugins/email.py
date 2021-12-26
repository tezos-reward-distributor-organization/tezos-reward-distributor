import logging
from plugins import plugins

# Plugin-specific libs
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, formataddr
from os.path import basename

logger = logging.getLogger("main.plugins.email")

plugin_name = "EmailPlugin"


class EmailPlugin(plugins.Plugin):

    _req_cfg_keys = [
        "smtp_user",
        "smtp_pass",
        "smtp_host",
        "smtp_port",
        "smtp_tls",
        "smtp_sender",
        "smtp_recipients",
    ]

    def __init__(self, cfg):
        super().__init__("Email", cfg["email"])

        logger.info(
            "[EmailPlugin] From: {:s}, To: [{:s}], Via: {:s}:{:d} ({:s}SSL/TLS)".format(
                self.sender,
                ", ".join(self.recipients),
                self.host,
                self.port,
                "" if self.use_tls else "No ",
            )
        )

    def send_admin_notification(
        self, subject, message, attachments=None, reward_data=None
    ):

        self.send_email(subject, message, attachments)

        logger.info("[EmailPlugin] Notification '{:s}' sent".format(subject))

    def send_payout_notification(self, cycle, payout_amount, nb_delegators):
        logger.debug("[EmailPlugin] Payout notification not implemented")
        return

    def send_email(self, subject, message, attachments):

        # Create email and basic headers
        msg = MIMEMultipart()

        if self.sender_name is not None:
            msg["From"] = formataddr((self.sender_name, self.sender))
        else:
            msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = subject

        msg.attach(MIMEText(message))

        # Any attachements?
        if attachments is not None:
            for f in attachments:
                with open(f, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=basename(f))

                # After the file is closed
                part["Content-Disposition"] = 'attachment; filename="%s"' % basename(f)
                msg.attach(part)

        # Connection
        smtp = smtplib.SMTP(self.host, self.port)
        if self.use_tls:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            smtp.starttls(context=ssl_context)
            smtp.ehlo()

        if not self.nologin:
            smtp.login(self.user, self.password)
        smtp.sendmail(self.sender, self.recipients, msg.as_string())
        smtp.close()

    def validateConfig(self):
        """Check that that passed config contains all the necessary
        parameters to run the Plugin
        """
        cfg_keys = self.cfg.keys()

        for k in self._req_cfg_keys:
            if k not in cfg_keys:
                raise plugins.PluginConfigurationError(
                    "[{:s}] {:s} config key not found".format(self.name, k)
                )

        # Set config
        self.host = self.cfg["smtp_host"]
        self.port = self.cfg["smtp_port"]
        self.use_tls = self.cfg["smtp_tls"]
        self.sender = self.cfg["smtp_sender"]
        self.user = self.cfg["smtp_user"]
        self.password = self.cfg["smtp_pass"]
        if "smtp_nologin" not in self.cfg:
            self.cfg["smtp_nologin"] = False

        self.nologin = self.cfg["smtp_nologin"]

        if "smtp_sender_name" not in self.cfg:
            self.cfg["smtp_sender_name"] = None

        self.sender_name = self.cfg["smtp_sender_name"]

        self.recipients = self.cfg["smtp_recipients"]
        if not isinstance(self.recipients, list):
            raise plugins.PluginConfigurationError(
                "[{:s}] 'smtp_recipients' not configured correctly".format(self.name)
            )

        # Sanity check, when nologin is enabled smtp_user is not required
        if self.nologin and (self.host is None or self.recipients is None):
            raise plugins.PluginConfigurationError(
                "[{:s}] Not Configured".format(self.name)
            )
        # Sanity check, when nologin is disabled, smtp_user is required
        elif not self.nologin and (
            self.host is None or self.user is None or self.recipients is None
        ):
            raise plugins.PluginConfigurationError(
                "[{:s}] Not Configured".format(self.name)
            )
