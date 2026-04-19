import { Plus, Trash2 } from "lucide-react";
import type { HttpRequestActionConfig } from "../nodeConfig";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH", "DELETE"]);

interface Props {
  config: HttpRequestActionConfig;
  onChange: (config: HttpRequestActionConfig) => void;
}

export function HttpRequestActionForm({ config, onChange }: Props) {
  function set<K extends keyof HttpRequestActionConfig>(
    key: K,
    value: HttpRequestActionConfig[K],
  ) {
    onChange({ ...config, [key]: value });
  }

  function addHeader() {
    onChange({ ...config, headers: [...config.headers, { key: "", value: "" }] });
  }

  function updateHeader(index: number, field: "key" | "value", val: string) {
    const updated = config.headers.map((h, i) => (i === index ? { ...h, [field]: val } : h));
    onChange({ ...config, headers: updated });
  }

  function removeHeader(index: number) {
    onChange({ ...config, headers: config.headers.filter((_, i) => i !== index) });
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
          placeholder="E.g. Fetch weather data"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Method + URL */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Method &amp; URL <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-2">
          <select
            value={config.method}
            onChange={(e) => set("method", e.target.value)}
            className="w-24 shrink-0 rounded-lg border border-gray-300 px-2 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {HTTP_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            type="url"
            value={config.url_template}
            onChange={(e) => set("url_template", e.target.value)}
            placeholder="https://api.example.com/{{path}}"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Use <code className="rounded bg-gray-100 px-1">{"{{variable}}"}</code> to reference prior step outputs
        </p>
      </div>

      {/* Headers */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Headers</label>
          <button
            type="button"
            onClick={addHeader}
            className="flex items-center gap-1 rounded text-xs text-blue-600 hover:text-blue-700"
          >
            <Plus className="h-3 w-3" />
            Add
          </button>
        </div>
        <div className="space-y-2">
          {config.headers.length === 0 && (
            <p className="text-xs text-gray-400">No headers added.</p>
          )}
          {config.headers.map((h, i) => (
            <div key={i} className="flex gap-2">
              <input
                type="text"
                value={h.key}
                onChange={(e) => updateHeader(i, "key", e.target.value)}
                placeholder="Header name"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <input
                type="text"
                value={h.value}
                onChange={(e) => updateHeader(i, "value", e.target.value)}
                placeholder="Value"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => removeHeader(i)}
                className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Body — only methods that actually carry one */}
      {METHODS_WITH_BODY.has(config.method) && (
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Body
          </label>
          <textarea
            value={config.body_template}
            onChange={(e) => set("body_template", e.target.value)}
            placeholder={'{\n  "text": "Hello from FlowPilot"\n}'}
            rows={6}
            className="w-full resize-y rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Sent verbatim as the request body. For JSON APIs (Slack, Discord,
            Notion…) remember to add a{" "}
            <code className="rounded bg-gray-100 px-1">Content-Type</code>{" "}
            header above.
          </p>
        </div>
      )}
    </div>
  );
}
