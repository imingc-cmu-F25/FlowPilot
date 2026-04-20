from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionSchema, ActionType, BaseAction


class SendEmailActionStep(BaseModel):
    action_type: Literal[ActionType.SEND_EMAIL] = ActionType.SEND_EMAIL
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    to_template: str
    subject_template: str
    body_template: str
    input_mapping: dict[str, str] = {}

    def validate_step(self) -> None:
        if not self.to_template:
            raise ValueError("to_template is required")
        if not self.subject_template:
            raise ValueError("subject_template is required")


class SendEmailAction(BaseAction):
    schema = ActionSchema(
        id="send_email",
        name="Send Email",
        description="Sends an email via SendGrid or SMTP",
        connector_id="smtp",
        config_fields=[
            {"name": "to", "type": "string", "required": True},
            {"name": "subject", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": True},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        from app.core.config import settings

        if settings.sendgrid_api_key:
            return await self._send_via_sendgrid(inputs, settings)
        return await self._send_via_smtp(inputs, settings)

    async def _send_via_sendgrid(self, inputs: dict, settings) -> dict:
        import httpx

        sender = settings.sendgrid_from or settings.smtp_from
        payload = {
            "personalizations": [{"to": [{"email": inputs["to"]}]}],
            "from": {"email": sender},
            "subject": inputs["subject"],
            "content": [{"type": "text/plain", "value": inputs["body"]}],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        if resp.status_code not in (200, 202):
            raise RuntimeError(
                f"SendGrid error {resp.status_code}: {resp.text}"
            )
        return {"status": "sent", "to": inputs["to"]}

    async def _send_via_smtp(self, inputs: dict, settings) -> dict:
        import asyncio
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = inputs["to"]
        msg["Subject"] = inputs["subject"]
        msg.set_content(inputs["body"])

        def _send():
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)

        await asyncio.to_thread(_send)
        return {"status": "sent", "to": inputs["to"]}
