import { useCallback, useEffect, useMemo, useState } from "react";
import { FileText, Sparkles, RefreshCw } from "lucide-react";
import {
  fetchReportsForOwner,
  generateReport,
  type MonthlyReport,
} from "../lib/api";
import { getStoredUsername } from "../auth/storage";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return iso;
  }
}

function formatPeriod(start: string, end: string): string {
  return `${formatDate(start)} – ${formatDate(end)}`;
}

function formatPct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

function previousMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const firstOfThisMonth = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1),
  );
  const endExclusive = firstOfThisMonth;
  const start = new Date(
    Date.UTC(firstOfThisMonth.getUTCFullYear(), firstOfThisMonth.getUTCMonth() - 1, 1),
  );
  return {
    start: start.toISOString(),
    end: new Date(endExclusive.getTime() - 1).toISOString(),
  };
}

export function ReportsPage() {
  const owner = getStoredUsername();
  const [reports, setReports] = useState<MonthlyReport[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!owner) {
      setLoading(false);
      setError("Sign in to view your reports.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReportsForOwner(owner);
      setReports(data);
      if (data.length > 0 && selectedId === null) {
        setSelectedId(data[0].report_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [owner, selectedId]);

  useEffect(() => {
    void load();
    // Intentionally only depend on owner — reloading on selectedId would
    // clobber the user's selection after each load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [owner]);

  const handleGenerate = async () => {
    if (!owner) return;
    setGenerating(true);
    setError(null);
    try {
      const { start, end } = previousMonthBounds();
      const created = await generateReport({
        owner_name: owner,
        period_start: start,
        period_end: end,
      });
      setReports((prev) => [created, ...prev]);
      setSelectedId(created.report_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const selected = useMemo(
    () => reports.find((r) => r.report_id === selectedId) ?? null,
    [reports, selectedId],
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Reports</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monthly summaries of your workflow automation activity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void load()}
            disabled={loading || !owner}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => void handleGenerate()}
            disabled={generating || !owner}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            {generating ? "Generating…" : "Generate last month"}
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-gray-600">Loading…</p>
      ) : reports.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
          <FileText className="mx-auto h-10 w-10 text-gray-400" />
          <p className="mt-3 text-sm text-gray-600">
            No reports yet. Click "Generate last month" to create one.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
          <ul className="space-y-2">
            {reports.map((r) => {
              const active = r.report_id === selectedId;
              return (
                <li key={r.report_id}>
                  <button
                    onClick={() => setSelectedId(r.report_id)}
                    className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                      active
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 bg-white hover:bg-gray-50"
                    }`}
                  >
                    <p className="text-sm font-medium text-gray-900">
                      {formatPeriod(r.period_start, r.period_end)}
                    </p>
                    <p className="mt-1 text-xs text-gray-600">
                      {r.metrics.total_runs} runs ·{" "}
                      {formatPct(r.metrics.success_rate)} success
                    </p>
                    <p className="mt-1 text-xs uppercase tracking-wide text-gray-500">
                      {r.status}
                    </p>
                  </button>
                </li>
              );
            })}
          </ul>

          {selected && <ReportDetail report={selected} />}
        </div>
      )}
    </div>
  );
}

function ReportDetail({ report }: { report: MonthlyReport }) {
  const {
    total_runs,
    success_count,
    failure_count,
    success_rate,
    avg_duration_seconds,
    runs_per_workflow,
    top_error_messages,
  } = report.metrics;

  const perWorkflow = Object.entries(runs_per_workflow);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-6 border-b border-gray-100 pb-4">
        <p className="text-xs uppercase tracking-wide text-gray-500">Period</p>
        <p className="mt-1 text-lg font-semibold text-gray-900">
          {formatPeriod(report.period_start, report.period_end)}
        </p>
      </div>

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-700">
          AI Summary
        </h2>
        <p className="whitespace-pre-wrap rounded-lg bg-blue-50 p-4 text-sm text-gray-800">
          {report.ai_summary || "(no summary)"}
        </p>
      </section>

      <section className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Total runs" value={total_runs.toString()} />
        <Stat label="Succeeded" value={success_count.toString()} />
        <Stat label="Failed" value={failure_count.toString()} />
        <Stat label="Success rate" value={formatPct(success_rate)} />
        <Stat label="Avg duration" value={formatDuration(avg_duration_seconds)} />
      </section>

      {perWorkflow.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-700">
            Runs by workflow
          </h2>
          <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
            {perWorkflow.map(([wfId, count]) => (
              <li
                key={wfId}
                className="flex items-center justify-between px-4 py-2 text-sm"
              >
                <span className="truncate font-mono text-xs text-gray-600">
                  {wfId}
                </span>
                <span className="font-medium text-gray-900">{count}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {top_error_messages.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-700">
            Top errors
          </h2>
          <ul className="space-y-2">
            {top_error_messages.map((msg, i) => (
              <li
                key={i}
                className="rounded-lg border border-red-100 bg-red-50 px-4 py-2 text-sm text-red-800"
              >
                {msg}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
