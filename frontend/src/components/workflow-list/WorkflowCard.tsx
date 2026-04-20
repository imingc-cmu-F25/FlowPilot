import { Link } from "react-router";
import { MoreVertical, Play, Zap } from "lucide-react";

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
  onRun?: () => void;
  running?: boolean;
  // Enable/disable toggle. Controlled from the parent so the list view can
  // optimistically flip the badge and roll back on error.
  onToggleEnabled?: (next: boolean) => void;
  togglingEnabled?: boolean;
  runs?: {
    run_id: string;
    status: string;
    triggered_at: string;
    trigger_type: string;
    error: string | null;
  }[];
}

const STATUS_COLORS: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700",
  retrying: "bg-yellow-100 text-yellow-700",
  pending: "bg-yellow-100 text-yellow-700",
};

function formatRelative(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
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
  onRun,
  running,
  onToggleEnabled,
  togglingEnabled,
  runs,
}: WorkflowCardProps) {
  const isActive = status === "active";
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
            <Zap className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{name}</h3>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                  isActive ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"
                }`}
              >
                {isActive ? "Active" : "Disabled"}
              </span>
              {onToggleEnabled && (
                <button
                  type="button"
                  role="switch"
                  aria-checked={isActive}
                  aria-label={isActive ? "Disable workflow" : "Enable workflow"}
                  disabled={togglingEnabled}
                  onClick={() => onToggleEnabled(!isActive)}
                  className={`relative inline-flex h-5 w-9 flex-none items-center rounded-full transition-colors disabled:opacity-60 ${
                    isActive ? "bg-green-500" : "bg-gray-300"
                  }`}
                  title={isActive ? "Click to disable" : "Click to enable"}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                      isActive ? "translate-x-[18px]" : "translate-x-0.5"
                    }`}
                  />
                </button>
              )}
            </div>
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
                  to={`/dashboard/workflow/builder/${id}`}
                  className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Edit
                </Link>
                <button
                  onClick={onDelete}
                  className="w-full rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      <p className="mb-4 text-sm text-gray-600">{description || "No description"}</p>
      <div className="mb-4 flex items-center justify-between text-sm">
        <span className="text-gray-500">Trigger: {triggerType}</span>
        <span className="text-gray-400">Updated: {updatedAt}</span>
      </div>

      {onRun ? (
        <button
          onClick={onRun}
          disabled={running}
          className="mb-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-60"
        >
          <Play className="h-4 w-4" />
          {running ? "Running…" : "Run now"}
        </button>
      ) : null}

      {runs && runs.length > 0 ? (
        <div className="border-t border-gray-100 pt-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
            Recent runs
          </p>
          <ul className="space-y-1.5">
            {runs.slice(0, 5).map((r) => (
              <li key={r.run_id}>
                <Link
                  to={`/dashboard/workflow/${id}/runs/${r.run_id}`}
                  className="-mx-2 flex items-center justify-between gap-2 rounded px-2 py-1 text-xs transition-colors hover:bg-gray-50"
                  title={r.error ?? "View execution log"}
                >
                  <span
                    className={`rounded-full px-2 py-0.5 font-medium ${
                      STATUS_COLORS[r.status] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {r.status}
                  </span>
                  <span className="text-gray-500">{r.trigger_type}</span>
                  <span className="text-gray-400">
                    {formatRelative(r.triggered_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
