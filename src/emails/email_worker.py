import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from os.path import basename


class EmailSender():
    def __init__(self, host, port, user, passw, sender, use_ssl: False):
        super(EmailSender, self).__init__()
        self.use_ssl = use_ssl
        self.host = host
        self.port = port
        self.sender = sender
        self.user = user
        self.password = passw

    def send(self, title, message, recipients, attachments):
        recipient_string = ", ".join(recipients) if type(recipients) == list else recipients

        msg = MIMEMultipart()
        msg['From'] = self.sender
        msg['To'] = recipient_string
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = title

        msg.attach(MIMEText(message))

        for f in attachments:
            with open(f, "rb") as fil:
                part = MIMEApplication(
                    fil.read(),
                    Name=basename(f)
                )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
            msg.attach(part)

        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.host, self.port)
        else:
            smtp = smtplib.SMTP(self.host, self.port)

        smtp.login(self.user, self.password)
        smtp.sendmail(self.sender, recipient_string, msg.as_string())
        smtp.close()


if __name__ == '__main__':
    sender = EmailSender("---", 587, "---", "---", "---")
    sender.send("---", "---", "---", [])
