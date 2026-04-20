import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  Activity,
  CheckCircle2,
  Plus,
  Play,
  TrendingUp,
  Zap,
  Clock,
  Webhook,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import {
  fetchWorkflowRuns,
  fetchWorkflows,
  type RunStatus,
  type WorkflowDefinition,
  type WorkflowRun,
} from "../lib/api";

type RunWithWorkflow = WorkflowRun & {
  workflow_name: string;
  workflow_trigger_type: string;
};

// Map backend status/trigger vocabulary to the human-friendly labels shown
// in the design. Keeping this local (rather than in api.ts) because it is
// purely a presentational concern for this page.
const TRIGGER_LABELS: Record<string, string> = {
  time: "Time-based",
  webhook: "Webhook",
  custom: "Custom",
  manual: "Manual",
};

function triggerLabel(type: string): string {
  return TRIGGER_LABELS[type] ?? type;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return iso;
  const diffMs = Date.now() - d;
  const sec = Math.round(diffMs / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} minute${min === 1 ? "" : "s"} ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hour${hr === 1 ? "" : "s"} ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day} day${day === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString();
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [runs, setRuns] = useState<RunWithWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const wfs = await fetchWorkflows();
      setWorkflows(wfs);

      // Pull runs per workflow in parallel. Failures per-workflow are
      // swallowed so one broken workflow doesn't blank the whole dashboard.
      const runLists = await Promise.all(
        wfs.map((wf) =>
          fetchWorkflowRuns(wf.workflow_id)
            .then((rs) =>
              rs.map<RunWithWorkflow>((r) => ({
                ...r,
                workflow_name: wf.name,
                workflow_trigger_type: wf.trigger.type,
              })),
            )
            .catch(() => [] as RunWithWorkflow[]),
        ),
      );
      const flat = runLists.flat();
      flat.sort(
        (a, b) =>
          new Date(b.triggered_at).getTime() -
          new Date(a.triggered_at).getTime(),
      );
      setRuns(flat);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Soft refresh every 15 s so the page stays honest without hammering the API.
  useEffect(() => {
    const t = setInterval(() => void load(), 15_000);
    return () => clearInterval(t);
  }, [load]);

  const stats = useMemo(() => {
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

    const runsThisMonth = runs.filter(
      (r) => new Date(r.triggered_at).getTime() >= monthStart,
    );
    const terminal = runs.filter(
      (r) => r.status === "success" || r.status === "failed",
    );
    const successCount = terminal.filter((r) => r.status === "success").length;
    const successRate =
      terminal.length === 0 ? null : (successCount / terminal.length) * 100;

    return {
      total: workflows.length,
      active: workflows.filter((w) => w.enabled).length,
      monthlyExecutions: runsThisMonth.length,
      successRate,
    };
  }, [workflows, runs]);

  // Client-side paging is fine here: we already fetch every run in `load()`
  // for the stats cards, so we're just slicing what's in memory. If the
  // history ever grows large enough to matter, push this to the API
  // (`GET /workflows/runs?limit=&offset=`).
  const PAGE_SIZE = 10;
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(runs.length / PAGE_SIZE));
  // If the run list shrinks (e.g., after a refresh) reset to the last
  // available page instead of showing an empty table.
  useEffect(() => {
    if (page > totalPages - 1) setPage(Math.max(0, totalPages - 1));
  }, [page, totalPages]);

  const pagedRuns = useMemo(
    () => runs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    [runs, page],
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-semibold text-gray-900">Dashboard</h1>
        <Link
          to="/dashboard/workflow/builder"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          New Workflow
        </Link>
      </div>

      {error && (
        <p className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Workflows"
          value={loading ? "…" : String(stats.total)}
          icon={<Activity className="h-5 w-5 text-blue-600" />}
        />
        <StatCard
          label="Active Workflows"
          value={loading ? "…" : String(stats.active)}
          icon={<CheckCircle2 className="h-5 w-5 text-blue-600" />}
        />
        <StatCard
          label="Executions This Month"
          value={loading ? "…" : stats.monthlyExecutions.toLocaleString()}
          icon={<Play className="h-5 w-5 text-blue-600" />}
        />
        <StatCard
          label="Success Rate"
          value={
            loading
              ? "…"
              : stats.successRate === null
                ? "—"
                : `${stats.successRate.toFixed(1)}%`
          }
          icon={<TrendingUp className="h-5 w-5 text-blue-600" />}
        />
      </div>

      <section className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            Workflow Execution History
          </h2>
          {runs.length > 0 && (
            <span className="text-xs text-gray-500">
              {runs.length.toLocaleString()} total
            </span>
          )}
        </header>

        {loading && runs.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-sm text-gray-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading executions…
          </div>
        ) : runs.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  <th className="px-6 py-3">Workflow Name</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Trigger Type</th>
                  <th className="px-6 py-3">Last Run</th>
                </tr>
              </thead>
              <tbody>
                {pagedRuns.map((r) => (
                  <tr
                    key={r.run_id}
                    onClick={() =>
                      navigate(
                        `/dashboard/workflow/${r.workflow_id}/runs/${r.run_id}`,
                      )
                    }
                    className="cursor-pointer border-t border-gray-100 text-sm transition-colors hover:bg-blue-50/40"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {/* Workflow name still deep-links to the builder, stop
                          click from bubbling up to the row handler. */}
                      <Link
                        to={`/dashboard/workflow/builder/${r.workflow_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="hover:text-blue-600"
                      >
                        {r.workflow_name}
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-6 py-4 text-gray-700">
                      <TriggerChip type={r.trigger_type} />
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      <span className="inline-flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-gray-400" />
                        {relativeTime(r.triggered_at)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-gray-100 px-6 py-3 text-xs text-gray-600">
                <span>
                  Showing{" "}
                  <span className="font-medium text-gray-800">
                    {page * PAGE_SIZE + 1}
                  </span>
                  –
                  <span className="font-medium text-gray-800">
                    {Math.min((page + 1) * PAGE_SIZE, runs.length)}
                  </span>{" "}
                  of{" "}
                  <span className="font-medium text-gray-800">
                    {runs.length.toLocaleString()}
                  </span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Prev
                  </button>
                  <span className="tabular-nums text-gray-500">
                    Page {page + 1} / {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }
                    disabled={page >= totalPages - 1}
                    className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
}

function StatCard({ label, value, icon }: StatCardProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <div>
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      </div>
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
        {icon}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: RunStatus }) {
  const styles: Record<RunStatus, string> = {
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    failed: "border-red-200 bg-red-50 text-red-700",
    running: "border-blue-200 bg-blue-50 text-blue-700",
    retrying: "border-amber-200 bg-amber-50 text-amber-700",
    pending: "border-amber-200 bg-amber-50 text-amber-700",
  };
  const icons: Record<RunStatus, React.ReactNode> = {
    success: <CheckCircle className="h-3 w-3" />,
    failed: <XCircle className="h-3 w-3" />,
    running: <Loader2 className="h-3 w-3 animate-spin" />,
    retrying: <RefreshCw className="h-3 w-3 animate-spin" />,
    pending: <Clock className="h-3 w-3" />,
  };
  const label =
    status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {icons[status]}
      {label}
    </span>
  );
}

function TriggerChip({ type }: { type: string }) {
  const icon =
    type === "time" ? (
      <Clock className="h-3.5 w-3.5" />
    ) : type === "webhook" ? (
      <Webhook className="h-3.5 w-3.5" />
    ) : type === "custom" ? (
      <Sparkles className="h-3.5 w-3.5" />
    ) : (
      <Zap className="h-3.5 w-3.5" />
    );
  return (
    <span className="inline-flex items-center gap-1.5 text-gray-700">
      <span className="text-gray-400">{icon}</span>
      {triggerLabel(type)}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
        <AlertTriangle className="h-6 w-6 text-blue-600" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-gray-900">
        No executions yet
      </h3>
      <p className="mt-1 max-w-sm text-sm text-gray-500">
        Create a workflow and hit <span className="font-medium">Run now</span>{" "}
        — or set up a trigger — to see recent executions here.
      </p>
      <Link
        to="/dashboard/workflow/builder"
        className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        <Plus className="h-4 w-4" />
        Create your first workflow
      </Link>
    </div>
  );
}
