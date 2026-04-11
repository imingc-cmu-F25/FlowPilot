import { GripVertical, Trash2 } from "lucide-react";

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
  return (
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
            onRemove();
          }}
          className="rounded p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
          aria-label="Remove node"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
