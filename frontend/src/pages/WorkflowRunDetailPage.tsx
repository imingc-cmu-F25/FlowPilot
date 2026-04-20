import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  RefreshCw,
  XCircle,
  AlertTriangle,
  SkipForward,
} from "lucide-react";
import {
  fetchStepRuns,
  fetchWorkflow,
  fetchWorkflowRun,
  type RunStatus,
  type WorkflowDefinition,
  type WorkflowRun,
  type WorkflowStepRun,
} from "../lib/api";

// Map action_type strings (backend `ActionType` StrEnum values) to friendly
// labels. Keep in sync with backend/app/action/base.py::ActionType.
const ACTION_LABELS: Record<string, string> = {
  http_request: "HTTP Request",
  send_email: "Send Email",
  calendar_create_event: "Create Calendar Event",
  calendar_list_upcoming: "List Upcoming Events",
};

function actionLabel(type: string): string {
  return ACTION_LABELS[type] ?? type;
}

function formatAbsolute(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatDuration(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string {
  if (!startIso) return "—";
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return "—";
  const ms = Math.max(0, end - start);
  if (ms < 1000) return `${ms}ms`;
  const sec = ms / 1000;
  if (sec < 60) return `${sec.toFixed(2)}s`;
  const min = Math.floor(sec / 60);
  const restSec = Math.round(sec - min * 60);
  return `${min}m ${restSec}s`;
}

function isTerminal(status: RunStatus): boolean {
  return status === "success" || status === "failed";
}

export function WorkflowRunDetailPage() {
  const { wfId, runId } = useParams();
  const navigate = useNavigate();

  const [workflow, setWorkflow] = useState<WorkflowDefinition | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [steps, setSteps] = useState<WorkflowStepRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!wfId || !runId) return;
      if (!opts?.silent) setLoading(true);
      setError(null);
      try {
        const [wf, r, stepRows] = await Promise.all([
          // Workflow fetch is cheap and gives us the display name; failures
          // here shouldn't block the run detail, so swallow and fall back.
          fetchWorkflow(wfId).catch(() => null),
          fetchWorkflowRun(wfId, runId),
          fetchStepRuns(wfId, runId),
        ]);
        if (wf) setWorkflow(wf);
        setRun(r);
        stepRows.sort((a, b) => a.step_order - b.step_order);
        setSteps(stepRows);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load run.");
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    [wfId, runId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  // While the run is still progressing the backend is writing new rows, so
  // keep polling quietly. Once it hits a terminal state, stop — the data is
  // immutable and we don't want to thrash the API.
  useEffect(() => {
    if (!run || isTerminal(run.status)) return;
    const timer = setInterval(() => void load({ silent: true }), 3000);
    return () => clearInterval(timer);
  }, [run, load]);

  const toggle = (order: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(order)) next.delete(order);
      else next.add(order);
      return next;
    });
  };

  const title = workflow?.name ?? "Workflow run";

  // The failing step is the one the engine stopped at. Useful to auto-
  // expand so the user doesn't have to hunt through a 10-step run for the
  // one red card.
  const autoExpanded = useMemo(() => {
    const failing = steps.find((s) => s.status === "failed");
    if (!failing) return null;
    return failing.step_order;
  }, [steps]);

  useEffect(() => {
    if (autoExpanded === null) return;
    setExpanded((prev) => {
      if (prev.has(autoExpanded)) return prev;
      const next = new Set(prev);
      next.add(autoExpanded);
      return next;
    });
  }, [autoExpanded]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="mb-2 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <h1 className="text-2xl font-semibold text-gray-900">
            {title}
            <span className="ml-2 text-sm font-normal text-gray-400">
              run {runId?.slice(0, 8)}…
            </span>
          </h1>
          {workflow && (
            <Link
              to={`/dashboard/workflow/builder/${workflow.workflow_id}`}
              className="mt-1 inline-block text-xs font-medium text-blue-600 hover:text-blue-700"
            >
              Open workflow definition →
            </Link>
          )}
        </div>
        <button
          onClick={() => void load()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          disabled={loading}
        >
          <RefreshCw
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Run summary */}
      {run && (
        <section className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <RunStatusBadge status={run.status} />
            <span className="text-xs text-gray-500">
              Triggered by{" "}
              <span className="font-medium text-gray-700">
                {run.trigger_type}
              </span>
            </span>
            {!isTerminal(run.status) && (
              <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                <Loader2 className="h-3 w-3 animate-spin" />
                live · auto-refreshing
              </span>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-500">
                Triggered
              </dt>
              <dd className="mt-0.5 text-gray-800">
                {formatAbsolute(run.triggered_at)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-500">
                Started
              </dt>
              <dd className="mt-0.5 text-gray-800">
                {formatAbsolute(run.started_at)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-500">
                Finished
              </dt>
              <dd className="mt-0.5 text-gray-800">
                {formatAbsolute(run.finished_at)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-500">
                Duration
              </dt>
              <dd className="mt-0.5 text-gray-800">
                {formatDuration(run.started_at, run.finished_at)}
              </dd>
            </div>
            {(run.retry_count ?? 0) > 0 && (
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-wide text-gray-500">
                  Retries
                </dt>
                <dd className="mt-0.5 text-gray-800">
                  {run.retry_count} / {run.max_retries ?? 0}
                </dd>
              </div>
            )}
          </dl>

          {run.error && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
              <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-red-700">
                <AlertTriangle className="h-3.5 w-3.5" />
                Run-level error
              </div>
              <pre className="whitespace-pre-wrap break-words font-mono text-xs text-red-900">
                {run.error}
              </pre>
            </div>
          )}
        </section>
      )}

      {/* Steps timeline */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Step execution log ({steps.length})
        </h2>

        {loading && steps.length === 0 ? (
          <div className="flex items-center justify-center rounded-xl border border-gray-200 bg-white py-12 text-sm text-gray-500">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading step logs…
          </div>
        ) : steps.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-6 py-10 text-center text-sm text-gray-500">
            No step executions have been recorded yet. If the run is still{" "}
            <span className="font-medium">pending</span>, give the engine a
            moment and refresh.
          </div>
        ) : (
          <ol className="space-y-3">
            {steps.map((step) => (
              <StepCard
                key={step.id}
                step={step}
                isExpanded={expanded.has(step.step_order)}
                onToggle={() => toggle(step.step_order)}
              />
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

interface StepCardProps {
  step: WorkflowStepRun;
  isExpanded: boolean;
  onToggle: () => void;
}

function StepCard({ step, isExpanded, onToggle }: StepCardProps) {
  const hasError = !!step.error;
  const hasDetails =
    hasError ||
    (step.inputs && Object.keys(step.inputs).length > 0) ||
    (step.output && Object.keys(step.output).length > 0);

  return (
    <li
      className={`overflow-hidden rounded-xl border bg-white shadow-sm ${
        step.status === "failed"
          ? "border-red-200"
          : step.status === "success"
            ? "border-gray-200"
            : "border-gray-200"
      }`}
    >
      <button
        onClick={onToggle}
        disabled={!hasDetails}
        className={`flex w-full items-center gap-3 px-4 py-3 text-left ${
          hasDetails ? "hover:bg-gray-50" : "cursor-default"
        }`}
      >
        {hasDetails ? (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 flex-none text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 flex-none text-gray-400" />
          )
        ) : (
          <span className="h-4 w-4 flex-none" />
        )}
        <div className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-700">
          {step.step_order + 1}
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-gray-900">
              {step.step_name}
            </div>
            <div className="truncate text-xs text-gray-500">
              {actionLabel(step.action_type)}
            </div>
          </div>
          <StepStatusBadge status={step.status} />
          <span className="hidden text-xs text-gray-500 sm:inline">
            {formatDuration(step.started_at, step.finished_at)}
          </span>
        </div>
      </button>

      {isExpanded && hasDetails && (
        <div className="space-y-3 border-t border-gray-100 bg-gray-50 p-4">
          {hasError && (
            <DetailBlock
              label="Error"
              tone="error"
              rawText={step.error ?? ""}
            />
          )}
          {step.inputs && Object.keys(step.inputs).length > 0 && (
            <DetailBlock label="Inputs (rendered)" data={step.inputs} />
          )}
          {step.output && Object.keys(step.output).length > 0 && (
            <DetailBlock label="Output" data={step.output} />
          )}
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-500 sm:grid-cols-4">
            <div>
              <dt className="font-medium text-gray-400">Started</dt>
              <dd>{formatAbsolute(step.started_at)}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-400">Finished</dt>
              <dd>{formatAbsolute(step.finished_at)}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-400">Step ID</dt>
              <dd className="truncate font-mono">{step.id}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-400">Action type</dt>
              <dd className="truncate font-mono">{step.action_type}</dd>
            </div>
          </dl>
        </div>
      )}
    </li>
  );
}

interface DetailBlockProps {
  label: string;
  data?: Record<string, unknown> | null;
  rawText?: string;
  tone?: "error";
}

function DetailBlock({ label, data, rawText, tone }: DetailBlockProps) {
  const body = rawText ?? JSON.stringify(data, null, 2);
  const isError = tone === "error";
  return (
    <div>
      <div
        className={`mb-1 text-xs font-semibold uppercase tracking-wide ${
          isError ? "text-red-700" : "text-gray-500"
        }`}
      >
        {label}
      </div>
      <pre
        className={`max-h-80 overflow-auto rounded-lg border p-3 font-mono text-xs ${
          isError
            ? "border-red-200 bg-red-50 text-red-900"
            : "border-gray-200 bg-white text-gray-800"
        }`}
      >
        {body}
      </pre>
    </div>
  );
}

function RunStatusBadge({ status }: { status: RunStatus }) {
  const styles: Record<RunStatus, string> = {
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    failed: "border-red-200 bg-red-50 text-red-700",
    running: "border-blue-200 bg-blue-50 text-blue-700",
    retrying: "border-amber-200 bg-amber-50 text-amber-700",
    pending: "border-amber-200 bg-amber-50 text-amber-700",
  };
  const icons: Record<RunStatus, React.ReactNode> = {
    success: <CheckCircle className="h-3.5 w-3.5" />,
    failed: <XCircle className="h-3.5 w-3.5" />,
    running: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    retrying: <RefreshCw className="h-3.5 w-3.5 animate-spin" />,
    pending: <Clock className="h-3.5 w-3.5" />,
  };
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {icons[status]}
      {label}
    </span>
  );
}

function StepStatusBadge({
  status,
}: {
  status: WorkflowStepRun["status"];
}) {
  const styles: Record<WorkflowStepRun["status"], string> = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    failed: "bg-red-50 text-red-700 border-red-200",
    skipped: "bg-gray-50 text-gray-600 border-gray-200",
  };
  const icons: Record<WorkflowStepRun["status"], React.ReactNode> = {
    success: <CheckCircle className="h-3 w-3" />,
    failed: <XCircle className="h-3 w-3" />,
    skipped: <SkipForward className="h-3 w-3" />,
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}
    >
      {icons[status]}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
