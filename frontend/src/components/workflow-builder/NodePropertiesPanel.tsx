import { X } from "lucide-react";
import { FormField } from "../FormField";

interface NodePropertiesPanelProps {
  type: "trigger" | "action";
  title: string;
  config: string;
  onTitleChange: (value: string) => void;
  onConfigChange: (value: string) => void;
  onClose: () => void;
}

export function NodePropertiesPanel({
  type,
  title,
  config,
  onTitleChange,
  onConfigChange,
  onClose,
}: NodePropertiesPanelProps) {
  return (
    <div className="w-80 overflow-y-auto border-l border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Properties</h3>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close properties"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="space-y-4">
        <FormField
          id="node-type"
          label="Node Type"
          value={type === "trigger" ? "Trigger" : "Action"}
          onChange={() => {}}
          disabled
        />
        <FormField
          id="node-title"
          label="Title"
          value={title}
          onChange={onTitleChange}
        />
        <div>
          <label htmlFor="node-details" className="mb-1 block text-sm font-medium text-gray-700">
            Details
          </label>
          <textarea
            id="node-details"
            rows={4}
            value={config}
            onChange={(e) => onConfigChange(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Enter additional details or notes..."
          />
        </div>
      </div>
    </div>
  );
}
