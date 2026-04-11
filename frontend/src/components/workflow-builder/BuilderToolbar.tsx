import { useState } from "react";
import { Save, Sparkles, AlertTriangle, Trash2 } from "lucide-react";

interface BuilderToolbarProps {
  workflowName: string;
  isEnabled: boolean;
  showAIChat: boolean;
  onNameChange: (name: string) => void;
  onEnabledChange: (enabled: boolean) => void;
  onToggleAIChat: () => void;
  onSave: () => void;
  onDiscard: () => void;
  saving?: boolean;
}

export function BuilderToolbar({
  workflowName,
  isEnabled,
  showAIChat,
  onNameChange,
  onEnabledChange,
  onToggleAIChat,
  onSave,
  onDiscard,
  saving = false,
}: BuilderToolbarProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <>
      <div className="border-b border-gray-200 bg-white px-4 py-3 sm:px-6 sm:py-4">
        {/* Row 1 (always): name + enabled */}
        <div className="flex items-center justify-between gap-2">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => onNameChange(e.target.value)}
            className="min-w-0 flex-1 truncate border-0 bg-transparent text-lg font-semibold text-gray-900 focus:outline-none focus:ring-0 sm:text-xl"
          />
          <label className="flex shrink-0 items-center gap-2">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => onEnabledChange(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">Enabled</span>
          </label>
        </div>

        {/* Row 2: action buttons — wrap on narrow screens */}
        <div className="mt-3 flex flex-wrap items-center justify-end gap-2 sm:mt-0 sm:pl-8">
          {/* On sm+ show inline with row 1 via absolute-ish trick; simpler: just flex-wrap handles it */}
          <button
            onClick={onToggleAIChat}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors sm:px-4 sm:py-2 ${
              showAIChat
                ? "border-purple-300 bg-purple-50 text-purple-700"
                : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            <Sparkles className="mr-1.5 inline h-4 w-4 sm:mr-2" />
            <span className="hidden xs:inline">AI </span>Assistant
          </button>
          <button
            onClick={() => setConfirming(true)}
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:border-red-300 hover:bg-red-50 sm:gap-2 sm:px-4 sm:py-2"
          >
            <Trash2 className="h-4 w-4" />
            Discard
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 sm:gap-2 sm:px-4 sm:py-2"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      {/* Discard confirmation dialog */}
      {confirming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
            <div className="mb-3 flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span className="text-base font-semibold">Discard workflow?</span>
            </div>
            <p className="mb-6 text-sm text-gray-600">
              All changes to this workflow will be lost and cannot be recovered.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirming(false)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Keep editing
              </button>
              <button
                onClick={() => { setConfirming(false); onDiscard(); }}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
