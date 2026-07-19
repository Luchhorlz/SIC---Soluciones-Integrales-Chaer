from __future__ import annotations

import asyncio
import html
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from .repository import PendingEmail, SqlAlchemyNotificationRepository


@dataclass(frozen=True)
class SmtpConfiguration:
    host: str | None
    port: int
    user: str | None
    password: str | None
    sender: str | None
    use_tls: bool
    app_url: str

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender)


class NotificationEmailDispatcher:
    def __init__(self, repository: SqlAlchemyNotificationRepository, configuration: SmtpConfiguration) -> None:
        self.repository = repository
        self.configuration = configuration

    def _send(self, pending: PendingEmail) -> None:
        notification = pending.notification
        message = EmailMessage()
        message["Subject"] = f"SIC — {notification.title}"
        message["From"] = self.configuration.sender
        message["To"] = pending.recipient_email
        link = f"{self.configuration.app_url.rstrip('/')}{notification.link_path}" if notification.link_path else self.configuration.app_url
        plain = f"Hola {pending.recipient_name},\n\n{notification.body}\n\nAbrir SIC: {link}\n\nEste es un aviso transaccional de Soluciones Integrales Chaer."
        safe_body = html.escape(notification.body)
        safe_link = html.escape(link, quote=True)
        message.set_content(plain)
        message.add_alternative(f"<p>Hola {html.escape(pending.recipient_name)},</p><p>{safe_body}</p><p><a href=\"{safe_link}\">Abrir SIC</a></p><p><small>Aviso transaccional de Soluciones Integrales Chaer.</small></p>", subtype="html")
        with smtplib.SMTP(self.configuration.host, self.configuration.port, timeout=15) as smtp:
            if self.configuration.use_tls:
                smtp.starttls()
            if self.configuration.user and self.configuration.password:
                smtp.login(self.configuration.user, self.configuration.password)
            smtp.send_message(message)

    async def dispatch(self, limit: int = 50) -> int:
        if not self.configuration.configured:
            return 0
        sent = 0
        for _index in range(limit):
            claimed = await self.repository.pending_emails(1)
            if not claimed:
                break
            pending = claimed[0]
            try:
                await asyncio.to_thread(self._send, pending)
                await self.repository.email_sent(pending.notification)
                sent += 1
            except Exception as error:
                await self.repository.email_failed(pending.notification, f"SMTP delivery failed: {type(error).__name__}")
        return sent
