import httpx

from app.core.email.provider import EmailProvider

MANDRILL_SEND_URL = "https://mandrillapp.com/api/1.0/messages/send"


class MandrillProvider(EmailProvider):
    def __init__(self, api_key: str, from_addr: str):
        self.api_key = api_key
        self.from_addr = from_addr

    def send(self, to: str, subject: str, body: str) -> bool:
        payload = {
            "key": self.api_key,
            "message": {
                "from_email": self.from_addr,
                "subject": subject,
                "text": body,
                "to": [{"email": to, "type": "to"}],
            },
        }
        resp = httpx.post(MANDRILL_SEND_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return True
