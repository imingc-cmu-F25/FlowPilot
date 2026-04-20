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
from datetime import UTC, datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


# Public catalogue of names the evaluator exposes. The API's dry-run
# endpoint and the frontend hint block both read this so we don't drift
# the docs vs the runtime env. Keep entries terse — the form UI lists
# them verbatim.
AVAILABLE_VARIABLES: tuple[tuple[str, str], ...] = (
    ("hour", "Current hour in the trigger's timezone, 0–23"),
    ("minute", "Current minute in the trigger's timezone, 0–59"),
    ("weekday", "Day of week (trigger TZ), Monday=0 … Sunday=6"),
    ("day", "Day of month (trigger TZ), 1–31"),
    ("month", "Month number (trigger TZ), 1–12"),
    ("year", "Full year (trigger TZ), e.g. 2026"),
    ("now", "Current time in the trigger's timezone, ISO-8601"),
    ("timezone", "The IANA timezone string, e.g. 'Asia/Taipei'"),
    ("source", "Value of the trigger's `source` config field"),
    ("true / false", "Boolean literals"),
)


def _resolve_tz(name: str | None) -> tuple[tzinfo, str]:
    """Return a (tzinfo, resolved_name) pair, falling back to UTC on bad input.

    We do NOT raise when the configured zone is unknown: a user editing
    their workflow shouldn't see the dispatcher silently stop on typo.
    The builder UI validates on the frontend; if something invalid still
    reaches the worker, UTC is the safe default.
    """
    candidate = (name or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(candidate), candidate
    except (ZoneInfoNotFoundError, ValueError):
        return UTC, "UTC"


def _build_env(config: CustomTriggerConfig) -> dict[str, Any]:
    """Build the whitelisted name→value environment exposed to user expressions.

    Kept deliberately flat and side-effect free: no callables, no objects with
    dunder methods that could be abused, just primitives and simple strings.
    Time-related names are computed in ``config.timezone`` (defaults to UTC),
    matching the way TimeTriggerConfig interprets its stored moment so users
    don't have to mentally convert zones when moving between trigger types.
    """
    tz, resolved = _resolve_tz(getattr(config, "timezone", None))
    now = datetime.now(tz)
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
        "timezone": resolved,
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


def dry_run_condition(
    condition: str,
    source: str = "event_payload",
    timezone: str = "UTC",
) -> dict[str, Any]:
    """Evaluate *condition* with the live clock and return a debug report.

    Shape: ``{ok: bool, value: bool | None, error: str | None, env: dict}``.
    ``ok=True`` means the expression parsed and evaluated cleanly; ``value``
    is the coerced bool outcome. ``ok=False`` means parsing or evaluation
    failed and ``error`` contains a human-readable reason — we want this
    to feed the builder UI directly, not the Celery dispatch loop, so
    here we *do* surface the failure instead of silently returning False.

    ``env`` echoes the variables that were visible to the expression so
    the UI can show "right now, weekday=2, hour=14, …" alongside the
    verdict. Time-related variables are evaluated in ``timezone`` (IANA
    zone); unknown zones fall back to UTC.
    """
    expr = (condition or "").strip()
    cfg = CustomTriggerConfig(
        condition=expr or "true", source=source, timezone=timezone or "UTC"
    )
    env = _build_env(cfg)
    visible_env = {
        k: v
        for k, v in env.items()
        # Hide Python-style aliases (True/False/None) from the surface
        # report; their lowercase twins are already there.
        if k not in {"True", "False", "None"}
    }
    if not expr:
        return {
            "ok": False,
            "value": None,
            "error": "Condition is empty.",
            "env": visible_env,
        }
    try:
        result = _safe_eval(expr, env)
    except _UnsafeExpressionError as exc:
        return {"ok": False, "value": None, "error": str(exc), "env": visible_env}
    except SyntaxError as exc:
        return {
            "ok": False,
            "value": None,
            "error": f"Syntax error: {exc.msg}",
            "env": visible_env,
        }
    except (TypeError, ValueError) as exc:
        return {"ok": False, "value": None, "error": str(exc), "env": visible_env}
    return {
        "ok": True,
        "value": bool(result),
        "error": None,
        "env": visible_env,
    }
