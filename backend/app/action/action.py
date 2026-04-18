"""
action.py — public facade for the action module.

All code should import from here. Sub-modules import from base.py only.
"""

from typing import Annotated

from pydantic import Field

# Re-export base types so callers only need `from app.action.action import ...`
from app.action.base import ActionSchema, ActionType, BaseAction, StepSpec  # noqa: F401
from app.action.calendarAction import CalendarActionStep, CalendarCreateEventAction  # noqa: F401

# Concrete step models (each imports from base.py — no circular dependency)
from app.action.httpRequestAction import HttpRequestAction, HttpRequestActionStep  # noqa: F401
from app.action.sendEmailAction import SendEmailAction, SendEmailActionStep  # noqa: F401

# Alias to match original name used in tests
CalendarCreateEventActionStep = CalendarActionStep

# Discriminated union — used as WorkflowDefinition.steps element type
ActionStep = Annotated[
    HttpRequestActionStep | SendEmailActionStep | CalendarActionStep,
    Field(discriminator="action_type"),
]

# Factory
_STEP_CONSTRUCTORS: dict[ActionType, type] = {
    ActionType.HTTP_REQUEST: HttpRequestActionStep,
    ActionType.SEND_EMAIL: SendEmailActionStep,
    ActionType.CALENDAR_CREATE_EVENT: CalendarActionStep,
}


class ActionStepFactory:
    @classmethod
    def create(
        cls, spec: StepSpec
    ) -> HttpRequestActionStep | SendEmailActionStep | CalendarActionStep:
        step_cls = _STEP_CONSTRUCTORS.get(spec.action_type)
        if step_cls is None:
            raise ValueError(f"Unknown action type: {spec.action_type}")
        step = step_cls(name=spec.name, step_order=spec.step_order, **spec.parameters)
        step.validate_step()
        return step

    @classmethod
    def register(cls, action_type: ActionType, step_cls: type) -> None:
        _STEP_CONSTRUCTORS[action_type] = step_cls
