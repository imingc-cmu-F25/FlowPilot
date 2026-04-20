"""CustomTrigger — fires when a user-supplied boolean expression is true.

The evaluator is deliberately small:

* It supports the subset of Python most users reach for when describing a
  "condition": comparisons, boolean connectives (and/or/not), membership
  (in / not in), numeric / string / bool / None literals, tuples, lists
  and sets of literals.
* It does **not** support attribute access, function calls, subscript
  beyond ``.get()``-style lookups, loops or assignments. Anything outside
  the whitelist raises at parse time and the condition is treated as
  false — a malformed expression must never crash the dispatch loop or,
  worse, execute arbitrary code.
* It ships with a curated context dict (current UTC time fields,
  configured source string, plus ``true``/``false`` aliases) so users can
  write things like ``hour == 8 and weekday in [0,1,2,3,4]`` to mean
  "weekday mornings at 08:00 UTC".

The result is a "safe enough" expression language for the coursework
demo without dragging in a full template engine or a DSL.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from typing import Any

from app.trigger.trigger import BaseTrigger, TriggerSchema
from app.trigger.triggerConfig import CustomTriggerConfig

# Node classes we permit inside a custom trigger condition. Everything
# else is rejected at parse time.
_ALLOWED_NODES: tuple[type, ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Mod,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Tuple,
    ast.List,
    ast.Set,
)


class _UnsafeExpressionError(Exception):
    """Raised when a condition string contains a disallowed construct."""


def _eval_node(node: ast.AST, env: dict[str, Any]) -> Any:
    if not isinstance(node, _ALLOWED_NODES):
        raise _UnsafeExpressionError(
            f"Unsupported expression element: {type(node).__name__}"
        )

    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in env:
            raise _UnsafeExpressionError(f"Unknown name: {node.id}")
        return env[node.id]

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, env)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand

    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, env)
        right = _eval_node(node.right, env)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Mod):
            return left % right

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env)
        for op, comparator in zip(node.ops, node.comparators, strict=False):
            right = _eval_node(comparator, env)
            if isinstance(op, ast.Eq) and not left == right:
                return False
            if isinstance(op, ast.NotEq) and not left != right:
                return False
            if isinstance(op, ast.Lt) and not left < right:
                return False
            if isinstance(op, ast.LtE) and not left <= right:
                return False
            if isinstance(op, ast.Gt) and not left > right:
                return False
            if isinstance(op, ast.GtE) and not left >= right:
                return False
            if isinstance(op, ast.In) and left not in right:
                return False
            if isinstance(op, ast.NotIn) and left in right:
                return False
            left = right
        return True

    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return [_eval_node(e, env) for e in node.elts]

    raise _UnsafeExpressionError(f"Unsupported node: {type(node).__name__}")


def _safe_eval(expr: str, env: dict[str, Any]) -> Any:
    """Parse *expr* as a Python expression and evaluate with whitelisted nodes only."""
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree, env)


def _build_env(config: CustomTriggerConfig) -> dict[str, Any]:
    """Build the whitelisted name→value environment exposed to user expressions.

    Kept deliberately flat and side-effect free: no callables, no objects with
    dunder methods that could be abused, just primitives and simple strings.
    """
    now = datetime.now(UTC)
    return {
        "true": True,
        "false": False,
        "True": True,
        "False": False,
        "None": None,
        "now": now.isoformat(),
        "hour": now.hour,
        "minute": now.minute,
        "weekday": now.weekday(),  # Monday = 0 … Sunday = 6
        "day": now.day,
        "month": now.month,
        "year": now.year,
        "source": config.source,
    }


class CustomTrigger(BaseTrigger):
    schema = TriggerSchema(
        id="custom",
        name="Custom",
        description=(
            "Fires when a user-defined boolean expression evaluates to true. "
            "Available names: hour, minute, weekday, day, month, year, now, "
            "source, true, false. Example: hour == 8 and weekday in [0,1,2,3,4]"
        ),
        config_fields=[
            {
                "name": "condition",
                "type": "string",
                "required": True,
                "description": (
                    "Boolean Python expression using the provided context names. "
                    "Unknown names or unsupported constructs evaluate to false."
                ),
            },
            {
                "name": "source",
                "type": "string",
                "required": False,
                "default": "event_payload",
                "description": "Opaque tag exposed to the expression as `source`",
            },
            {
                "name": "description",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Human-readable explanation of this custom trigger",
            },
        ],
    )

    async def evaluate(self, context: dict) -> bool:
        config: CustomTriggerConfig = context["config"]
        expr = (config.condition or "").strip()
        if not expr:
            return False

        # Fast-path literal shortcuts so users who set condition="true" /
        # "false" (the previous behaviour) still see the same outcome even
        # if the wider expression evaluator were to change.
        lowered = expr.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False

        env = _build_env(config)
        try:
            return bool(_safe_eval(expr, env))
        except (SyntaxError, _UnsafeExpressionError, TypeError, ValueError):
            # Any parse / evaluation failure is treated as "don't fire".
            # We intentionally swallow so a bad condition in one workflow
            # can't starve the dispatch loop for every other workflow.
            return False
