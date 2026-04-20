import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ChevronDown, Loader2, XCircle } from "lucide-react";
import { browserTimezone, type CustomTriggerConfig } from "../nodeConfig";
import {
  evaluateCustomCondition,
  type CustomTriggerDryRunResponse,
} from "../../../lib/api";

interface Props {
  config: CustomTriggerConfig;
  onChange: (config: CustomTriggerConfig) => void;
}

// Snippets the user can click to get started. Phrased without a hard-coded
// zone suffix — the currently-selected timezone is shown once in the hint
// strip below, so repeating it on every chip is noise. Each expression
// maps to a real use case: weekday reminders, business hours, monthly
// tasks, weekend-only, N-minute cadence.
const EXAMPLES: { label: string; expr: string; hint: string }[] = [
  {
    label: "Weekdays at 08:00",
    expr: "hour == 8 and minute == 0 and weekday in [0,1,2,3,4]",
    hint: "Fires once, at the top of 08:00 — wire to a daily digest.",
  },
  {
    label: "Business hours (09:00–17:59)",
    expr: "hour >= 9 and hour < 18",
    hint: "Fires every minute inside the window. Add a dedup in the action.",
  },
  {
    label: "1st of every month",
    expr: "day == 1 and hour == 0 and minute == 0",
    hint: "Monthly kickoff at midnight.",
  },
  {
    label: "Every 15 minutes",
    expr: "minute % 15 == 0",
    hint: "Matches :00, :15, :30, :45.",
  },
  {
    label: "Weekend only",
    expr: "weekday in [5, 6]",
    hint: "Fires every minute on Sat/Sun.",
  },
];

const OPERATOR_HINTS = [
  "== != < <= > >=",
  "and / or / not",
  "in / not in",
  "+ - * %",
];

type PreviewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | {
      kind: "ok";
      value: boolean;
      env: CustomTriggerDryRunResponse["env"];
      variables: CustomTriggerDryRunResponse["available_variables"];
    }
  | { kind: "error"; message: string };

function verdictTone(state: PreviewState): {
  bg: string;
  border: string;
  text: string;
  Icon: typeof CheckCircle2;
  label: string;
} {
  if (state.kind === "loading")
    return {
      bg: "bg-gray-50",
      border: "border-gray-200",
      text: "text-gray-600",
      Icon: Loader2,
      label: "Evaluating…",
    };
  if (state.kind === "error")
    return {
      bg: "bg-red-50",
      border: "border-red-200",
      text: "text-red-700",
      Icon: XCircle,
      label: "Invalid",
    };
  if (state.kind === "ok" && state.value)
    return {
      bg: "bg-green-50",
      border: "border-green-200",
      text: "text-green-700",
      Icon: CheckCircle2,
      label: "Would fire right now",
    };
  return {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-700",
    Icon: AlertCircle,
    label: "Not true at this moment",
  };
}

export function CustomTriggerForm({ config, onChange }: Props) {
  function set<K extends keyof CustomTriggerConfig>(
    key: K,
    value: CustomTriggerConfig[K],
  ) {
    onChange({ ...config, [key]: value });
  }

  const [preview, setPreview] = useState<PreviewState>({ kind: "idle" });
  // Cached variable catalogue so the hint block stays populated even while
  // a later request is in-flight (prevents the list from flickering out of
  // existence on every keystroke).
  const [variables, setVariables] = useState<
    CustomTriggerDryRunResponse["available_variables"]
  >([]);

  // A timezone is required for the evaluator to make sense. Existing
  // workflows saved before this field existed round-trip as "UTC"; pull
  // them forward to the browser's zone on first edit so the preview
  // matches what the user sees on the wall.
  const effectiveTz = config.timezone?.trim() || browserTimezone();

  // Debounced dry-run: every keystroke schedules a preview 350 ms out,
  // and each new keystroke cancels the pending one. Keeps the network
  // chatter tolerable while still feeling "live" in demo. We defer the
  // "loading"/"idle" marker to a microtask so the effect itself doesn't
  // call setState synchronously (avoids a cascading re-render warning
  // and keeps the visible state consistent with the latest keystroke).
  useEffect(() => {
    const expr = config.condition.trim();
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setPreview(expr ? { kind: "loading" } : { kind: "idle" });
    });
    if (!expr) {
      return () => {
        cancelled = true;
      };
    }
    const handle = window.setTimeout(async () => {
      try {
        const res = await evaluateCustomCondition(
          expr,
          config.source,
          effectiveTz,
        );
        if (res.available_variables.length > 0) {
          setVariables(res.available_variables);
        }
        if (res.ok && res.value !== null) {
          setPreview({
            kind: "ok",
            value: res.value,
            env: res.env,
            variables: res.available_variables,
          });
        } else {
          setPreview({
            kind: "error",
            message: res.error ?? "Condition is invalid.",
          });
        }
      } catch (e) {
        setPreview({
          kind: "error",
          message: e instanceof Error ? e.message : "Preview failed.",
        });
      }
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [config.condition, config.source, effectiveTz]);

  const tone = verdictTone(preview);

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Weekday morning digest"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Condition <span className="text-red-500">*</span>
        </label>
        <textarea
          value={config.condition}
          onChange={(e) => set("condition", e.target.value)}
          placeholder="hour == 8 and weekday in [0,1,2,3,4]"
          rows={2}
          spellCheck={false}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Times resolved in{" "}
          <span className="font-mono text-gray-700">{effectiveTz}</span>.
          Backend re-evaluates every minute; fires when the expression is
          truthy. Change the timezone under <em>Advanced</em> if needed.
        </p>

        {/* Live preview banner. Shows a loading state while debouncing,
            a concrete verdict once the backend replies, or the error
            reason verbatim so users know why the dispatcher would ignore
            their condition. Intentionally not framed as "pass/fail":
            "Not true at this moment" is the normal, expected state for
            most conditions outside their fire window. */}
        {preview.kind !== "idle" && (
          <div
            className={`mt-2 flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${tone.bg} ${tone.border} ${tone.text}`}
          >
            <tone.Icon
              className={`mt-0.5 h-4 w-4 shrink-0 ${
                preview.kind === "loading" ? "animate-spin" : ""
              }`}
            />
            <div className="min-w-0 flex-1">
              <p className="font-medium">{tone.label}</p>
              {preview.kind === "error" && (
                <p className="mt-0.5 break-words font-mono text-[11px] opacity-90">
                  {preview.message}
                </p>
              )}
              {preview.kind === "ok" && !preview.value && (
                <p className="mt-0.5 text-[11px] opacity-80">
                  Normal for most conditions — the workflow will fire as
                  soon as the expression becomes true (rechecked every
                  minute in {effectiveTz}).
                </p>
              )}
              {preview.kind === "ok" && preview.value && (
                <p className="mt-0.5 text-[11px] opacity-80">
                  If this workflow is enabled and saved, the backend
                  would emit a run this minute.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Example chips — one click fills the condition field. Intentionally
          low-ceremony: no "Are you sure?" confirm, because overwriting a
          starter value is the whole point. */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-gray-600">
          Starter examples — click to insert
        </p>
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.expr}
              type="button"
              title={`${ex.expr}\n\n${ex.hint}`}
              onClick={() => set("condition", ex.expr)}
              className="rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-700 transition-colors hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {/* Variable + operator catalogue. Variables come from the backend
          endpoint so we don't drift; operators are hand-curated because
          they're a subset of Python the evaluator whitelists. */}
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        <p className="mb-2 font-semibold">Available variables</p>
        <dl className="space-y-1.5">
          {(variables.length > 0
            ? variables
            : [
                {
                  name: "hour",
                  description: "Current hour in the trigger's timezone, 0–23",
                },
                {
                  name: "minute",
                  description:
                    "Current minute in the trigger's timezone, 0–59",
                },
                {
                  name: "weekday",
                  description:
                    "Day of week (trigger TZ), Monday=0 … Sunday=6",
                },
                {
                  name: "day",
                  description: "Day of month (trigger TZ), 1–31",
                },
                {
                  name: "month",
                  description: "Month number (trigger TZ), 1–12",
                },
                {
                  name: "year",
                  description: "Full year (trigger TZ), e.g. 2026",
                },
                {
                  name: "now",
                  description:
                    "Current time in the trigger's timezone, ISO-8601",
                },
                {
                  name: "timezone",
                  description:
                    "The IANA timezone string, e.g. 'Asia/Taipei'",
                },
                {
                  name: "source",
                  description: "Value of the `source` config field",
                },
                { name: "true / false", description: "Boolean literals" },
              ]
          ).map((v) => (
            <div key={v.name} className="flex flex-wrap items-baseline gap-2">
              <dt>
                <code className="rounded bg-blue-100 px-1 py-0.5 font-mono text-[11px]">
                  {v.name}
                </code>
              </dt>
              <dd className="text-[11px] text-blue-800">{v.description}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 mb-1 font-semibold">Supported operators</p>
        <div className="flex flex-wrap gap-1.5">
          {OPERATOR_HINTS.map((op) => (
            <code
              key={op}
              className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-[11px]"
            >
              {op}
            </code>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-blue-800">
          Attribute access (<code className="font-mono">x.y</code>), function
          calls, and imports are <strong>not</strong> allowed and will render
          the condition invalid.
        </p>
      </div>

      {/* Advanced: Timezone, Source, and Description are rarely touched
          and add cognitive load in the main view. Collapsed by default;
          users who need them can still reach them in one click. */}
      <details className="group rounded-lg border border-gray-200 bg-white">
        <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Advanced
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="space-y-3 border-t border-gray-100 px-3 py-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Timezone
            </label>
            <input
              type="text"
              value={config.timezone}
              onChange={(e) => set("timezone", e.target.value)}
              placeholder={browserTimezone()}
              spellCheck={false}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-[11px] text-gray-500">
              IANA zone (e.g.{" "}
              <code className="font-mono">Asia/Taipei</code>,{" "}
              <code className="font-mono">America/Los_Angeles</code>).
              Leave as your browser default (
              <code className="font-mono">{browserTimezone()}</code>)
              unless you need a specific zone. Unknown zones fall back to
              UTC at evaluation time.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Source
            </label>
            <input
              type="text"
              value={config.source}
              onChange={(e) => set("source", e.target.value)}
              placeholder="event_payload"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-[11px] text-gray-500">
              Opaque tag exposed to the expression as{" "}
              <code className="font-mono">source</code>. Leave as default
              unless you have a specific integration in mind.
            </p>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Description
            </label>
            <textarea
              value={config.description}
              onChange={(e) => set("description", e.target.value)}
              rows={2}
              placeholder="Notes for your future self about why this condition was chosen."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </details>
    </div>
  );
}
