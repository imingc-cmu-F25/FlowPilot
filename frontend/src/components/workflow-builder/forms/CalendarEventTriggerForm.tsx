import type { CalendarEventTriggerConfig } from "../nodeConfig";

interface Props {
  config: CalendarEventTriggerConfig;
  onChange: (config: CalendarEventTriggerConfig) => void;
}

export function CalendarEventTriggerForm({ config, onChange }: Props) {
  function set<K extends keyof CalendarEventTriggerConfig>(
    key: K,
    value: CalendarEventTriggerConfig[K],
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
          placeholder="E.g. On new calendar event"
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
        <p className="mt-1 text-xs text-gray-500">
          Use <code className="rounded bg-gray-100 px-1">primary</code> for your
          default Google Calendar.
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Only when title contains
        </label>
        <input
          type="text"
          value={config.title_contains}
          onChange={(e) => set("title_contains", e.target.value)}
          placeholder="standup, 1:1, interview…"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Optional — leave blank to fire on any new event.
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Debounce (seconds)
        </label>
        <input
          type="number"
          min={0}
          value={config.dedup_seconds}
          onChange={(e) =>
            set("dedup_seconds", Number(e.target.value) || 0)
          }
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Prevents the workflow from running twice when your calendar
          re-syncs in quick succession.
        </p>
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        <p className="mb-1 font-medium">How this trigger works</p>
        <p>
          FlowPilot syncs your Google Calendar every 10 minutes. When a new
          event lands on the cache, this trigger fires one workflow run.
          Pair it with the{" "}
          <span className="font-medium">List Upcoming Events</span> action
          to read the current agenda inside the workflow.
        </p>
      </div>
    </div>
  );
}
