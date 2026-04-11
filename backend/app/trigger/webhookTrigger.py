from app.trigger.trigger import BaseTrigger, TriggerSchema


class WebhookTrigger(BaseTrigger):
    """
    Fires when an HTTP request is received at the configured path.
    Push-driven: the HTTP handler verifies the request and fires the engine directly.
    """
    schema = TriggerSchema(
        id="webhook",
        name="Webhook",
        description="Fires when an HTTP request arrives at the configured path",
        config_fields=[
            {
                "name": "path",
                "type": "string",
                "required": True,
                "description": "URL path to listen on, e.g. /hooks/my-workflow",
            },
            {
                "name": "method",
                "type": "string",
                "required": False,
                "default": "POST",
                "description": "HTTP method to accept (GET, POST, PUT, PATCH, DELETE)",
            },
            {
                "name": "secret_ref",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Reference to a stored secret for HMAC signature verification",
            },
            {
                "name": "event_filter",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Match against X-Event-Type header; empty means accept any",
            },
            {
                "name": "header_filters",
                "type": "object",
                "required": False,
                "default": {},
                "description": "Additional header key→value pairs that must match",
            },
        ],
    )

    async def evaluate(self, _context: dict) -> bool:
        return True
