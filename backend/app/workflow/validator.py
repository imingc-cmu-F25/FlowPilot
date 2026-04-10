from app.workflow.workflow import WorkflowDefinition


def validate_workflow(wf: WorkflowDefinition) -> list[str]:
    """
    Return a list of error strings; empty list means the workflow is valid.
   
    Validation rules:
    - Workflow must have a trigger, and trigger config must be valid.
    - Workflow must have at least one action step.
    - step_order values must be unique across steps.
    - Each step validates its own required fields.
    """
    errors: list[str] = []

    # trigger presence
    if wf.trigger is None:
        errors.append("Workflow must have a trigger.")
    else:
        try:
            wf.trigger.validate_config()
        except ValueError as exc:
            errors.append(f"Trigger: {exc}")

    # has at least one action step
    if not wf.steps:
        errors.append("Workflow must have at least one action step.")

    # step_order values must be unique
    orders = [s.step_order for s in wf.steps]
    if len(orders) != len(set(orders)):
        errors.append("Duplicate step_order values found.")

    # each step validates its own required fields
    for step in wf.steps:
        try:
            step.validate_step()
        except ValueError as exc:
            errors.append(f"Step '{step.name}' (order {step.step_order}): {exc}")

    return errors
