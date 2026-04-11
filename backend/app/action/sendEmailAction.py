from typing import Literal
from uuid import uuid4, UUID
from pydantic import BaseModel, Field

from app.action.base import ActionType, ActionSchema, BaseAction


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
        description="Sends an email via SMTP connector",
        connector_id="smtp",
        config_fields=[
            {"name": "to", "type": "string", "required": True},
            {"name": "subject", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": True},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        """
        @param inputs: A dict with keys "to", "subject", "body"
        @return: A dict with the result of sending the email
        """
        import smtplib
        from email.message import EmailMessage

        from app.core.config import settings

        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = inputs["to"]
        msg["Subject"] = inputs["subject"]
        msg.set_content(inputs["body"])

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

        return {"status": "sent", "to": inputs["to"]}

