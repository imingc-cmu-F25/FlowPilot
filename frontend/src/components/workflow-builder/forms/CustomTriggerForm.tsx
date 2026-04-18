import type { CustomTriggerConfig } from "../nodeConfig";

interface Props {
  config: CustomTriggerConfig;
  onChange: (config: CustomTriggerConfig) => void;
}

export function CustomTriggerForm({ config, onChange }: Props) {
  function set<K extends keyof CustomTriggerConfig>(key: K, value: CustomTriggerConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Custom condition trigger"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Condition <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.condition}
          onChange={(e) => set("condition", e.target.value)}
          placeholder='Try "true" for demo'
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Source</label>
        <input
          type="text"
          value={config.source}
          onChange={(e) => set("source", e.target.value)}
          placeholder="event_payload"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
        <textarea
          value={config.description}
          onChange={(e) => set("description", e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}