import { useState } from "react";
import { AlertTriangle, GripVertical, Trash2 } from "lucide-react";

interface WorkflowNodeCardProps {
  title: string;
  config?: string;
  type: "trigger" | "action";
  icon: React.ElementType;
  selected: boolean;
  onClick: () => void;
  onRemove: () => void;
}

export function WorkflowNodeCard({
  title,
  config,
  type,
  icon: Icon,
  selected,
  onClick,
  onRemove,
}: WorkflowNodeCardProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <>
      <div
        onClick={onClick}
        className={`cursor-pointer rounded-lg border-2 bg-white p-4 shadow-sm transition-all ${
          selected ? "border-blue-500 ring-2 ring-blue-200" : "border-gray-200 hover:border-gray-300"
        }`}
      >
        <div className="flex items-center gap-3">
          <GripVertical className="h-5 w-5 text-gray-400" />
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
            <Icon className="h-5 w-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-gray-900">{title}</div>
            <div className="text-sm text-gray-500">{config}</div>
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              type === "trigger" ? "bg-purple-50 text-purple-700" : "bg-blue-50 text-blue-700"
            }`}
          >
            {type === "trigger" ? "Trigger" : "Action"}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setConfirming(true);
            }}
            className="rounded p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
            aria-label="Remove node"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {confirming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
            <div className="mb-3 flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span className="text-base font-semibold">
                Remove {type === "trigger" ? "trigger" : "action"}?
              </span>
            </div>
            <p className="mb-6 text-sm text-gray-600">
              This {type} will be removed from the workflow and cannot be recovered.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirming(false)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Keep
              </button>
              <button
                onClick={() => {
                  setConfirming(false);
                  onRemove();
                }}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
