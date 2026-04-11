import type { CalendarActionConfig } from "../nodeConfig";

interface Props {
  config: CalendarActionConfig;
  onChange: (config: CalendarActionConfig) => void;
}

export function CalendarActionForm({ config, onChange }: Props) {
  function set<K extends keyof CalendarActionConfig>(key: K, value: CalendarActionConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Create meeting"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Calendar ID */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Calendar ID <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.calendar_id}
          onChange={(e) => set("calendar_id", e.target.value)}
          placeholder="primary or user@example.com"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Event title */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Event title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.title_template}
          onChange={(e) => set("title_template", e.target.value)}
          placeholder="Meeting with {{name}}"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Start / End mappings */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Start time (JSONPath) <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.start_mapping}
          onChange={(e) => set("start_mapping", e.target.value)}
          placeholder="$.steps[0].output.start_time"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          End time (JSONPath) <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.end_mapping}
          onChange={(e) => set("end_mapping", e.target.value)}
          placeholder="$.steps[0].output.end_time"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <p className="text-xs text-gray-400">
        JSONPath references resolve against prior step outputs at runtime.
      </p>
    </div>
  );
}
