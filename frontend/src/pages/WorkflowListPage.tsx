import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { Plus } from "lucide-react";
import {
  deleteWorkflow,
  fetchWorkflowRuns,
  fetchWorkflows,
  triggerWorkflowRun,
  type WorkflowDefinition,
  type WorkflowRun,
} from "../lib/api";
import { WorkflowSearchBar } from "../components/workflow-list/WorkflowSearchBar";
import { WorkflowCard } from "../components/workflow-list/WorkflowCard";

type FilterValue = "all" | "active" | "disabled";

function toCardStatus(wf: WorkflowDefinition): "active" | "disabled" {
  return wf.enabled ? "active" : "disabled";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function WorkflowListPage() {
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterValue>("all");
  const [search, setSearch] = useState("");
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [runsById, setRunsById] = useState<Record<string, WorkflowRun[]>>({});
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set());

  const loadRuns = useCallback(async (workflowId: string) => {
    try {
      const runs = await fetchWorkflowRuns(workflowId);
      setRunsById((prev) => ({ ...prev, [workflowId]: runs }));
    } catch {
      // Silent — runs are a non-critical sidebar widget.
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWorkflows();
      setWorkflows(data);
      await Promise.all(data.map((wf) => loadRuns(wf.workflow_id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, [loadRuns]);

  useEffect(() => {
    void load();
  }, [load]);

  // Background refresh: triggers that fire from the backend (time / webhook /
  // custom) won't notify the frontend, so without this the "Recent runs" badge
  // would stay stale until the user reloads. 10 s is a pragmatic compromise —
  // fast enough that a one-minute time trigger visibly updates, slow enough
  // that we don't hammer the API.
  useEffect(() => {
    if (workflows.length === 0) return;
    const timer = setInterval(() => {
      workflows.forEach((wf) => {
        void loadRuns(wf.workflow_id);
      });
    }, 10_000);
    return () => clearInterval(timer);
  }, [workflows, loadRuns]);

  const handleRun = async (workflowId: string) => {
    setRunningIds((prev) => new Set(prev).add(workflowId));
    try {
      await triggerWorkflowRun(workflowId);
      // Poll a few times so the badge updates as the async run completes.
      for (let i = 0; i < 3; i++) {
        await new Promise((r) => setTimeout(r, 500));
        await loadRuns(workflowId);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to trigger run");
    } finally {
      setRunningIds((prev) => {
        const next = new Set(prev);
        next.delete(workflowId);
        return next;
      });
    }
  };

  const handleDelete = async (workflowId: string) => {
    const confirmed = window.confirm(
      "Delete this workflow? This action cannot be undone.",
    );
    if (!confirmed) return;
    setOpenMenu(null);
    try {
      await deleteWorkflow(workflowId);
      setWorkflows((prev) => prev.filter((w) => w.workflow_id !== workflowId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete workflow");
    }
  };

  const filteredWorkflows = workflows.filter((wf) => {
    const cardStatus = toCardStatus(wf);
    const matchesFilter = filter === "all" || cardStatus === filter;
    const matchesSearch = wf.name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">My Workflows</h1>
        <Link
          to="/dashboard/workflow/builder"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
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

      <WorkflowSearchBar
        search={search}
        filter={filter}
        onSearchChange={setSearch}
        onFilterChange={setFilter}
      />

      {loading ? (
        <p className="text-sm text-gray-600">Loading…</p>
      ) : filteredWorkflows.length === 0 ? (
        <p className="text-sm text-gray-600">
          {workflows.length === 0
            ? "No workflows yet. Create one to get started."
            : "No workflows match your search."}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredWorkflows.map((wf) => (
            <WorkflowCard
              key={wf.workflow_id}
              id={wf.workflow_id}
              name={wf.name}
              description={wf.description}
              triggerType={wf.trigger.type}
              status={toCardStatus(wf)}
              updatedAt={formatDate(wf.updated_at)}
              menuOpen={openMenu === wf.workflow_id}
              onToggleMenu={() =>
                setOpenMenu(openMenu === wf.workflow_id ? null : wf.workflow_id)
              }
              onDelete={() => handleDelete(wf.workflow_id)}
              onRun={() => handleRun(wf.workflow_id)}
              running={runningIds.has(wf.workflow_id)}
              runs={runsById[wf.workflow_id]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
