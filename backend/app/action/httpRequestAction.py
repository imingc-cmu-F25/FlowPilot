from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionSchema, ActionType, BaseAction


class HttpRequestActionStep(BaseModel):
    action_type: Literal[ActionType.HTTP_REQUEST] = ActionType.HTTP_REQUEST
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    method: str = "GET"
    url_template: str  # supports {{variable}} placeholders
    headers: dict[str, str] = {}
    # Raw request body sent verbatim (e.g. a JSON string for Slack / Discord
    # incoming webhooks). Kept as an opaque string because different services
    # expect different media types; the user is expected to set the matching
    # Content-Type via `headers`.
    body_template: str = ""
    input_mapping: dict[str, str] = {}  # param name → JSONPath into prior output

    def validate_step(self) -> None:
        if not self.url_template:
            raise ValueError("url_template is required")
        if self.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"Unsupported HTTP method: {self.method}")


class HttpRequestAction(BaseAction):
    """
    Makes an HTTP request to an external URL, returning the response
    """
    schema = ActionSchema(
        id="http_request",
        name="HTTP Request",
        description="Makes an HTTP request to an external URL",
        config_fields=[
            {"name": "method", "type": "string", "required": True},
            {"name": "url", "type": "string", "required": True},
            {"name": "headers", "type": "object", "required": False},
            {"name": "body", "type": "string", "required": False},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        """
        @param inputs: A dict with keys "method", "url", "headers", "body"
        @return: A dict with the HTTP response details
        """
        import httpx  # pip install httpx
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=inputs.get("method", "GET"),
                url=inputs["url"],
                headers=inputs.get("headers", {}),
                content=inputs.get("body"),
            )
        return {"status_code": response.status_code, "body": response.text}
