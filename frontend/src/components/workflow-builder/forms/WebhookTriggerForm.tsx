import type { WebhookTriggerConfig } from "../nodeConfig";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

interface Props {
  config: WebhookTriggerConfig;
  onChange: (config: WebhookTriggerConfig) => void;
}

export function WebhookTriggerForm({ config, onChange }: Props) {
  function set<K extends keyof WebhookTriggerConfig>(key: K, value: WebhookTriggerConfig[K]) {
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
          placeholder="E.g. GitHub push hook"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Path */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Path <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.path}
          onChange={(e) => set("path", e.target.value)}
          placeholder="/hooks/my-workflow"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">Must start with /</p>
      </div>

      {/* Method */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">HTTP method</label>
        <select
          value={config.method}
          onChange={(e) => set("method", e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {HTTP_METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Secret ref */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Secret reference
          <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="text"
          value={config.secret_ref}
          onChange={(e) => set("secret_ref", e.target.value)}
          placeholder="my-webhook-secret"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Used for HMAC signature verification
        </p>
      </div>

      {/* Event filter */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Event filter
          <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="text"
          value={config.event_filter}
          onChange={(e) => set("event_filter", e.target.value)}
          placeholder="push"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Matches against X-Event-Type header; empty = accept any
        </p>
      </div>
    </div>
  );
}
