import { Save, Play, Sparkles } from "lucide-react";

interface BuilderToolbarProps {
  workflowName: string;
  isEnabled: boolean;
  showAIChat: boolean;
  onNameChange: (name: string) => void;
  onEnabledChange: (enabled: boolean) => void;
  onToggleAIChat: () => void;
  onRunTest: () => void;
  onSave: () => void;
}

export function BuilderToolbar({
  workflowName,
  isEnabled,
  showAIChat,
  onNameChange,
  onEnabledChange,
  onToggleAIChat,
  onRunTest,
  onSave,
}: BuilderToolbarProps) {
  return (
    <div className="border-b border-gray-200 bg-white px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => onNameChange(e.target.value)}
            className="border-0 bg-transparent text-xl font-semibold text-gray-900 focus:outline-none focus:ring-0"
          />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => onEnabledChange(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">Enabled</span>
          </label>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleAIChat}
            className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              showAIChat
                ? "border-purple-300 bg-purple-50 text-purple-700"
                : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            <Sparkles className="mr-2 inline h-4 w-4" />
            AI Assistant
          </button>
          <button
            onClick={onRunTest}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            <Play className="mr-2 inline h-4 w-4" />
            Run Test
          </button>
          <button
            onClick={onSave}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <Save className="mr-2 inline h-4 w-4" />
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
