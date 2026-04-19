import { Link } from "react-router";
import { MoreVertical, Zap } from "lucide-react";

interface WorkflowCardProps {
  id: string;
  name: string;
  description: string;
  triggerType: string;
  status: "active" | "disabled";
  updatedAt: string;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onDelete: () => void;
}

export function WorkflowCard({
  id,
  name,
  description,
  triggerType,
  status,
  updatedAt,
  menuOpen,
  onToggleMenu,
  onDelete,
}: WorkflowCardProps) {
  const builderPath = `/dashboard/workflow/builder/${id}`;

  return (
    <Link
      to={builderPath}
      className="block rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
            <Zap className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{name}</h3>
            <span
              className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                status === "active"
                  ? "bg-green-50 text-green-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {status === "active" ? "Active" : "Disabled"}
            </span>
          </div>
        </div>
        <div className="relative">
          <button
            onClick={onToggleMenu}
            className="rounded p-1 transition-colors hover:bg-gray-100"
          >
            <MoreVertical className="h-5 w-5 text-gray-400" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-8 z-10 w-40 rounded-lg border border-gray-200 bg-white shadow-lg">
              <div className="p-1">
                <Link
                  to={builderPath}
                  className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Edit
                </Link>
                <button
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    onDelete();
                  }}
                  className="w-full rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <p className="mb-4 text-sm text-gray-600">
        {description || "No description"}
      </p>
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500">Trigger: {triggerType}</span>
        <span className="text-gray-400">Updated: {updatedAt}</span>
      </div>
    </Link>
  );
}
