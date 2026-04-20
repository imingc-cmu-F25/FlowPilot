import type { CalendarListUpcomingActionConfig } from "../nodeConfig";
import { HintDL, HintIntro, HintItem, HintPanel } from "./hintPanel";

interface Props {
  config: CalendarListUpcomingActionConfig;
  onChange: (config: CalendarListUpcomingActionConfig) => void;
}

export function CalendarListUpcomingForm({ config, onChange }: Props) {
  function set<K extends keyof CalendarListUpcomingActionConfig>(
    key: K,
    value: CalendarListUpcomingActionConfig[K],
  ) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Name
        </label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Pull upcoming meetings"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Calendar ID
        </label>
        <input
          type="text"
          value={config.calendar_id}
          onChange={(e) => set("calendar_id", e.target.value)}
          placeholder="primary"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Window (hours ahead)
        </label>
        <input
          type="number"
          min={0}
          max={8760}
          value={config.window_hours}
          onChange={(e) =>
            set("window_hours", Math.max(0, Number(e.target.value) || 0))
          }
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Only return events starting within this many hours from now.{" "}
          <code className="rounded bg-gray-100 px-1">0</code> = no cap (just
          max results).{" "}
          <code className="rounded bg-gray-100 px-1">24</code> = today +
          rollover.{" "}
          <code className="rounded bg-gray-100 px-1">168</code> = this week.
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Max results
        </label>
        <input
          type="number"
          min={1}
          max={100}
          value={config.max_results}
          onChange={(e) =>
            set("max_results", Math.max(1, Number(e.target.value) || 1))
          }
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Only events whose title contains
        </label>
        <input
          type="text"
          value={config.title_contains}
          onChange={(e) => set("title_contains", e.target.value)}
          placeholder="Optional, e.g. standup"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <HintPanel summary="How to use the result in the next step">
        <HintIntro>
          Drop these into a Send Email body / subject or an API Call URL /
          body:
        </HintIntro>
        <HintDL>
          <HintItem codes={["{{previous_output.agenda_text}}"]}>
            Pre-rendered bullet list, ideal for email bodies.
          </HintItem>
          <HintItem codes={["{{previous_output.count}}"]}>
            Number of events returned.
          </HintItem>
          <HintItem codes={["{{previous_output.events}}"]}>
            Structured list (auto-rendered as bullets of titles).
          </HintItem>
        </HintDL>
      </HintPanel>
    </div>
  );
}
