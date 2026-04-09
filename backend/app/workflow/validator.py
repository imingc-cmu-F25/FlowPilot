# workflow/validator.py

from app.workflow.Workflow import Workflow, StepType

class WorkflowValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors

def validate_workflow(wf: Workflow) -> list[str]:
    errors = []

    # 1. Exactly one trigger
    triggers = [s for s in wf.steps if s.step_type == StepType.TRIGGER]
    if len(triggers) != 1:
        errors.append(f"Workflow must have exactly 1 trigger, found {len(triggers)}.")

    # 2. Cycle detection via topological sort
    adj: dict[str, list[str]] = {str(s.id): [] for s in wf.steps}
    for e in wf.edges:
        adj[str(e.source_step_id)].append(str(e.target_step_id))

    visited, in_stack = set(), set()
    def has_cycle(node):
        visited.add(node); in_stack.add(node)
        for nb in adj.get(node, []):
            if nb in in_stack:
                return True
            if nb not in visited and has_cycle(nb):
                return True
        in_stack.discard(node)
        return False

    for node in adj:
        if node not in visited and has_cycle(node):
            errors.append("Workflow contains a cycle.")
            break

    # 3. Orphaned steps (no incoming or outgoing edge, excluding trigger)
    connected = set()
    for e in wf.edges:
        connected.add(str(e.source_step_id))
        connected.add(str(e.target_step_id))
    for s in wf.steps:
        if s.step_type != StepType.TRIGGER and str(s.id) not in connected:
            errors.append(f"Step '{s.name}' is disconnected.")

    # 4. Required config fields populated
    # (would cross-reference against ActionRegistry/TriggerRegistry schemas)

    return errors