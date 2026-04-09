import { useState } from "react";
import { Calendar, ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock as ClockIcon } from "lucide-react";

interface ExecutionLog {
  id: string;
  workflowName: string;
  trigger: string;
  status: "success" | "failed" | "running";
  startedAt: string;
  duration: string;
  steps?: {
    name: string;
    status: "success" | "failed";
    input: string;
    output: string;
    error?: string;
  }[];
}

export function ExecutionLogs() {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

  const executionLogs: ExecutionLog[] = [
    {
      id: "RUN-1001",
      workflowName: "Daily Task Reminder",
      trigger: "Time-based",
      status: "success",
      startedAt: "2026-04-08 09:00:15",
      duration: "1.2s",
      steps: [
        {
          name: "Send Email",
          status: "success",
          input: "to: user@example.com",
          output: "Email sent successfully",
        },
        {
          name: "Send Notification",
          status: "success",
          input: "message: Daily tasks ready",
          output: "Notification delivered",
        },
      ],
    },
    {
      id: "RUN-1002",
      workflowName: "Email Newsletter Digest",
      trigger: "Webhook",
      status: "success",
      startedAt: "2026-04-08 08:45:30",
      duration: "2.8s",
      steps: [
        {
          name: "API Call",
          status: "success",
          input: "endpoint: /api/newsletter",
          output: "Data retrieved",
        },
      ],
    },
    {
      id: "RUN-1003",
      workflowName: "Calendar Event Notifier",
      trigger: "Google Calendar",
      status: "failed",
      startedAt: "2026-04-08 07:30:00",
      duration: "0.5s",
      steps: [
        {
          name: "Fetch Calendar Events",
          status: "failed",
          input: "calendar_id: primary",
          output: "",
          error: "Authentication failed: Token expired",
        },
      ],
    },
    {
      id: "RUN-1004",
      workflowName: "Weekly Report Generator",
      trigger: "Time-based",
      status: "success",
      startedAt: "2026-04-08 06:00:00",
      duration: "4.3s",
      steps: [
        {
          name: "Generate Report",
          status: "success",
          input: "period: last_7_days",
          output: "Report generated",
        },
        {
          name: "Send Email",
          status: "success",
          input: "to: admin@example.com",
          output: "Email sent",
        },
      ],
    },
    {
      id: "RUN-1005",
      workflowName: "Assignment Deadline Alert",
      trigger: "Time-based",
      status: "success",
      startedAt: "2026-04-08 04:00:00",
      duration: "0.9s",
      steps: [
        {
          name: "Check Deadlines",
          status: "success",
          input: "date_range: next_24h",
          output: "3 deadlines found",
        },
        {
          name: "Send Notification",
          status: "success",
          input: "count: 3",
          output: "Notifications sent",
        },
      ],
    },
  ];

  const filteredLogs =
    statusFilter === "all"
      ? executionLogs
      : executionLogs.filter((log) => log.status === statusFilter);

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Execution History</h1>

      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Date Range</label>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Select date range"
              className="w-48 rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Workflow</label>
          <select className="w-56 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
            <option>All Workflows</option>
            <option>Daily Task Reminder</option>
            <option>Email Newsletter Digest</option>
            <option>Calendar Event Notifier</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-40 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Run ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Workflow Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Trigger
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Started At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-600">
                Details
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredLogs.map((log) => (
              <>
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-mono text-gray-900">{log.id}</td>
                  <td className="px-6 py-4 font-medium text-gray-900">{log.workflowName}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{log.trigger}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        log.status === "success"
                          ? "bg-green-50 text-green-700"
                          : log.status === "failed"
                          ? "bg-red-50 text-red-700"
                          : "bg-yellow-50 text-yellow-700"
                      }`}
                    >
                      {log.status === "success" ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : log.status === "failed" ? (
                        <XCircle className="h-3 w-3" />
                      ) : (
                        <ClockIcon className="h-3 w-3" />
                      )}
                      {log.status === "success"
                        ? "Success"
                        : log.status === "failed"
                        ? "Failed"
                        : "Running"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{log.startedAt}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{log.duration}</td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() =>
                        setExpandedRow(expandedRow === log.id ? null : log.id)
                      }
                      className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
                    >
                      {expandedRow === log.id ? (
                        <>
                          Hide <ChevronUp className="h-4 w-4" />
                        </>
                      ) : (
                        <>
                          View <ChevronDown className="h-4 w-4" />
                        </>
                      )}
                    </button>
                  </td>
                </tr>
                {expandedRow === log.id && log.steps && (
                  <tr>
                    <td colSpan={7} className="bg-gray-50 px-6 py-4">
                      <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-gray-900">Execution Steps</h4>
                        {log.steps.map((step, index) => (
                          <div
                            key={index}
                            className="rounded-lg border border-gray-200 bg-white p-4"
                          >
                            <div className="mb-2 flex items-center justify-between">
                              <span className="font-medium text-gray-900">{step.name}</span>
                              <span
                                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                                  step.status === "success"
                                    ? "bg-green-50 text-green-700"
                                    : "bg-red-50 text-red-700"
                                }`}
                              >
                                {step.status === "success" ? (
                                  <CheckCircle2 className="h-3 w-3" />
                                ) : (
                                  <XCircle className="h-3 w-3" />
                                )}
                                {step.status === "success" ? "Success" : "Failed"}
                              </span>
                            </div>
                            <div className="space-y-2 text-sm">
                              <div>
                                <span className="font-medium text-gray-700">Input: </span>
                                <span className="text-gray-600">{step.input}</span>
                              </div>
                              {step.output && (
                                <div>
                                  <span className="font-medium text-gray-700">Output: </span>
                                  <span className="text-gray-600">{step.output}</span>
                                </div>
                              )}
                              {step.error && (
                                <div className="rounded bg-red-50 p-2">
                                  <span className="font-medium text-red-700">Error: </span>
                                  <span className="text-red-600">{step.error}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
