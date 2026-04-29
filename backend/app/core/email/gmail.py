import smtplib
from email.mime.text import MIMEText

from app.core.email.provider import EmailProvider


class GmailSMTPProvider(EmailProvider):
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr

    def send(self, to: str, subject: str, body: str) -> bool:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.sendmail(self.from_addr, [to], msg.as_string())
        return True
