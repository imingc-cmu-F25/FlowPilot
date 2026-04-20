"""Minimal ``{{path.dot.notation}}`` template rendering for action inputs.

The workflow builder has always advertised ``{{variable}}`` placeholders
in its form hints (see e.g. ``SendEmailActionForm.tsx``), but until this
module existed there was no renderer — every ``_template`` field was
shipped to the wire verbatim. The result was surprising enough to look
like a user bug ("my email didn't contain the events!") so this module
exists to keep the advertised contract honest.

Semantics (deliberately small — this is *not* Jinja):
    * ``{{path}}`` or ``{{ path.to.value }}`` — replaced with the
      stringified value at that dotted path in ``context``. Whitespace
      inside the braces is ignored.
    * Unknown paths resolve to an empty string rather than raising, so
      a typo by the user at save-time doesn't crash the whole workflow
      run. The step's persisted ``inputs`` row still captures the raw
      template, so it's obvious from run history what was intended.
    * List-of-dict values are rendered as one ``- key: value`` line per
      item, using the first-present of ``title`` / ``name`` / ``id`` as
      the label. Lets users drop ``{{previous_output.events}}`` into an
      email body and get a readable digest without any extra config.
    * Dicts get ``json.dumps``'d so users at least see structured data
      instead of ``{"foo": ...}`` from ``str(dict)``.
    * Any other value is passed through ``str()``.

Anything more ambitious (conditionals, loops, filters) should wait for
a deliberate design pass — this is "make the common case work", not a
templating language.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Match `{{ anything_but_braces }}` with optional surrounding whitespace.
# Captures the raw path for the substitution function to resolve.
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def render_template(template: str, context: dict[str, Any]) -> str:
    """Render a ``{{path}}`` template against ``context``.

    Non-string inputs are returned unchanged so callers can blindly pass
    arbitrary fields through without type-guarding every one of them.
    """
    if not isinstance(template, str) or "{{" not in template:
        return template
    return _PLACEHOLDER_RE.sub(lambda m: _stringify(_resolve(context, m.group(1))), template)


def _resolve(context: dict[str, Any], path: str) -> Any:
    """Walk a ``a.b.c`` path through nested dicts / lists.

    Integer segments index into lists (``events.0.title``). A missing
    path returns ``None`` — the caller stringifies it to an empty
    string. We don't distinguish "path absent" from "value is None" on
    purpose: either way, there's nothing useful to emit.
    """
    cur: Any = context
    for part in path.split("."):
        if cur is None:
            return None
        key: Any = part
        if isinstance(cur, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue
        if isinstance(cur, dict):
            if key not in cur:
                return None
            cur = cur[key]
            continue
        return None
    return cur


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        # ``bool`` is a subclass of ``int`` in Python so this branch
        # must come before the int fallthrough to dumps.
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return _format_list(value)
    if isinstance(value, dict):
        return json.dumps(value, default=str, indent=2, sort_keys=True)
    return str(value)


def _format_list(items: list[Any]) -> str:
    if not items:
        return ""
    # Heuristic: if every item is a dict, render one bullet per item
    # using the first-present label key. Otherwise fall back to JSON so
    # mixed / primitive lists still produce something debuggable.
    if all(isinstance(x, dict) for x in items):
        lines: list[str] = []
        for item in items:
            label = (
                item.get("title")
                or item.get("name")
                or item.get("subject")
                or item.get("id")
                or json.dumps(item, default=str, sort_keys=True)
            )
            lines.append(f"- {label}")
        return "\n".join(lines)
    return json.dumps(items, default=str, indent=2)
