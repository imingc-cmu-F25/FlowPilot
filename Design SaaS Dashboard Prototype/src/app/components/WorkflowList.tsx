import { Link } from "react-router";
import { useState } from "react";
import { Plus, Search, MoreVertical, Clock, Webhook, Calendar } from "lucide-react";

interface Workflow {
  id: string;
  name: string;
  description: string;
  trigger: string;
  triggerIcon: any;
  status: "active" | "disabled";
  lastRun: string;
}

export function WorkflowList() {
  const [filter, setFilter] = useState<"all" | "active" | "disabled">("all");
  const [search, setSearch] = useState("");
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const workflows: Workflow[] = [
    {
      id: "1",
      name: "Daily Task Reminder",
      description: "Sends morning reminder for tasks",
      trigger: "Time-based",
      triggerIcon: Clock,
      status: "active",
      lastRun: "2 hours ago",
    },
    {
      id: "2",
      name: "Email Newsletter Digest",
      description: "Compiles weekly newsletter content",
      trigger: "Webhook",
      triggerIcon: Webhook,
      status: "active",
      lastRun: "1 day ago",
    },
    {
      id: "3",
      name: "Calendar Event Notifier",
      description: "Sends notifications for upcoming events",
      trigger: "Google Calendar",
      triggerIcon: Calendar,
      status: "disabled",
      lastRun: "3 days ago",
    },
    {
      id: "4",
      name: "Weekly Report Generator",
      description: "Creates weekly performance reports",
      trigger: "Time-based",
      triggerIcon: Clock,
      status: "active",
      lastRun: "6 hours ago",
    },
    {
      id: "5",
      name: "Assignment Deadline Alert",
      description: "Alerts for upcoming assignment deadlines",
      trigger: "Time-based",
      triggerIcon: Clock,
      status: "active",
      lastRun: "12 hours ago",
    },
    {
      id: "6",
      name: "Study Group Coordinator",
      description: "Manages study group scheduling",
      trigger: "Webhook",
      triggerIcon: Webhook,
      status: "disabled",
      lastRun: "1 week ago",
    },
  ];

  const filteredWorkflows = workflows.filter((workflow) => {
    const matchesFilter = filter === "all" || workflow.status === filter;
    const matchesSearch = workflow.name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">My Workflows</h1>
        <Link
          to="/dashboard/workflow/builder"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Workflow
        </Link>
      </div>

      <div className="mb-6 flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search workflows..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as any)}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="all">All Workflows</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredWorkflows.map((workflow) => {
          const Icon = workflow.triggerIcon;
          return (
            <div
              key={workflow.id}
              className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                    <Icon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{workflow.name}</h3>
                    <span
                      className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        workflow.status === "active"
                          ? "bg-green-50 text-green-700"
                          : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {workflow.status === "active" ? "Active" : "Disabled"}
                    </span>
                  </div>
                </div>
                <div className="relative">
                  <button
                    onClick={() => setOpenMenu(openMenu === workflow.id ? null : workflow.id)}
                    className="rounded p-1 hover:bg-gray-100 transition-colors"
                  >
                    <MoreVertical className="h-5 w-5 text-gray-400" />
                  </button>
                  {openMenu === workflow.id && (
                    <div className="absolute right-0 top-8 z-10 w-40 rounded-lg border border-gray-200 bg-white shadow-lg">
                      <div className="p-1">
                        <Link
                          to={`/dashboard/workflow/builder/${workflow.id}`}
                          className="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          Edit
                        </Link>
                        <button className="w-full rounded px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                          Duplicate
                        </button>
                        <button className="w-full rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50">
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <p className="mb-4 text-sm text-gray-600">{workflow.description}</p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Trigger: {workflow.trigger}</span>
                <span className="text-gray-400">Last run: {workflow.lastRun}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
