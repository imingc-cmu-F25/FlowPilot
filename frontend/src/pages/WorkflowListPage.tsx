import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { Plus } from "lucide-react";
import { fetchWorkflows, deleteWorkflow, type WorkflowDefinition } from "../lib/api";
import { WorkflowSearchBar } from "../components/workflow-list/WorkflowSearchBar";
import { WorkflowCard } from "../components/workflow-list/WorkflowCard";

type FilterValue = "all" | "active" | "disabled";

function toCardStatus(wf: WorkflowDefinition): "active" | "disabled" {
  return wf.enabled && wf.status === "active" ? "active" : "disabled";
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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWorkflows();
      setWorkflows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (workflowId: string) => {
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
          {workflows.length === 0 ? "No workflows yet. Create one to get started." : "No workflows match your search."}
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
            />
          ))}
        </div>
      )}
    </div>
  );
}
