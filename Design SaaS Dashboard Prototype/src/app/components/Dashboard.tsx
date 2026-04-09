import { Link } from "react-router";
import { Plus, Clock, Activity, TrendingUp, CheckCircle2, XCircle, PlayCircle } from "lucide-react";

export function Dashboard() {
  const stats = [
    { label: "Total Workflows", value: "12", icon: Activity },
    { label: "Active Workflows", value: "8", icon: CheckCircle2 },
    { label: "Executions This Month", value: "1,247", icon: PlayCircle },
    { label: "Success Rate", value: "94.2%", icon: TrendingUp },
  ];

  const recentExecutions = [
    {
      id: "1",
      workflow: "Daily Task Reminder",
      status: "success",
      trigger: "Time-based",
      lastRun: "2 minutes ago",
    },
    {
      id: "2",
      workflow: "Email Newsletter Digest",
      status: "success",
      trigger: "Webhook",
      lastRun: "15 minutes ago",
    },
    {
      id: "3",
      workflow: "Calendar Event Notifier",
      status: "failed",
      trigger: "Google Calendar",
      lastRun: "1 hour ago",
    },
    {
      id: "4",
      workflow: "Weekly Report Generator",
      status: "success",
      trigger: "Time-based",
      lastRun: "3 hours ago",
    },
    {
      id: "5",
      workflow: "Assignment Deadline Alert",
      status: "success",
      trigger: "Time-based",
      lastRun: "5 hours ago",
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <Link
          to="/dashboard/workflow/builder"
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create New Workflow
        </Link>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{stat.label}</p>
                  <p className="mt-2 text-3xl font-semibold text-gray-900">{stat.value}</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50">
                  <Icon className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Workflow Executions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                  Workflow Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                  Trigger Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                  Last Run
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recentExecutions.map((execution) => (
                <tr key={execution.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/dashboard/logs?workflow=${execution.workflow}`}
                      className="font-medium text-gray-900 hover:text-blue-600"
                    >
                      {execution.workflow}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        execution.status === "success"
                          ? "bg-green-50 text-green-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {execution.status === "success" ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : (
                        <XCircle className="h-3 w-3" />
                      )}
                      {execution.status === "success" ? "Success" : "Failed"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{execution.trigger}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {execution.lastRun}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
