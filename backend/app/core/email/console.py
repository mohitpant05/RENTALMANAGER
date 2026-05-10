import logging

from app.core.email.provider import EmailProvider

logger = logging.getLogger(__name__)


class ConsoleEmailProvider(EmailProvider):
    def __init__(self, from_addr: str):
        self.from_addr = from_addr

    def send(self, to: str, subject: str, body: str) -> bool:
        logger.info("=" * 60)
        logger.info("EMAIL (console provider)")
        logger.info("From:    %s", self.from_addr)
        logger.info("To:      %s", to)
        logger.info("Subject: %s", subject)
        logger.info("-" * 60)
        logger.info(body)
        logger.info("=" * 60)
        return True
