import { Download, ChevronLeft, ChevronRight } from "lucide-react";
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export function MonthlyReport() {
  const dailyExecutionData = [
    { day: "Apr 1", count: 42 },
    { day: "Apr 2", count: 38 },
    { day: "Apr 3", count: 45 },
    { day: "Apr 4", count: 51 },
    { day: "Apr 5", count: 48 },
    { day: "Apr 6", count: 44 },
    { day: "Apr 7", count: 52 },
    { day: "Apr 8", count: 36 },
  ];

  const statusDistributionData = [
    { name: "Success", value: 1175, color: "#10b981" },
    { name: "Failed", value: 52, color: "#ef4444" },
    { name: "Running", value: 20, color: "#f59e0b" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Monthly Report</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <button className="rounded p-1 hover:bg-gray-100 transition-colors">
              <ChevronLeft className="h-5 w-5 text-gray-600" />
            </button>
            <span className="text-sm font-medium text-gray-700">April 2026</span>
            <button className="rounded p-1 hover:bg-gray-100 transition-colors">
              <ChevronRight className="h-5 w-5 text-gray-600" />
            </button>
          </div>
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
            <Download className="h-4 w-4" />
            Download PDF
          </button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-600">Total Runs</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">1,247</p>
          <p className="mt-1 text-sm text-green-600">+12% from last month</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-600">Success Rate</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">94.2%</p>
          <p className="mt-1 text-sm text-green-600">+2.1% from last month</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-600">Time Saved</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">47.3h</p>
          <p className="mt-1 text-sm text-green-600">+8.5h from last month</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-600">Most Used</p>
          <p className="mt-2 text-lg font-semibold text-gray-900">Daily Task Reminder</p>
          <p className="mt-1 text-sm text-gray-500">342 executions</p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Daily Execution Count</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dailyExecutionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#6b7280" />
              <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Execution Status Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={statusDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {statusDistributionData.map((entry) => (
                  <Cell key={`cell-${entry.name}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">AI Summary</h2>
        <div className="rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 p-6">
          <p className="text-gray-800 leading-relaxed">
            This month showed strong automation performance with 1,247 total workflow executions, marking a 12% increase from the previous month. Your success rate improved to 94.2%, demonstrating excellent workflow reliability. The Daily Task Reminder workflow led usage with 342 executions, followed by Email Newsletter Digest with 287 runs. Time-based triggers accounted for 68% of all executions, while webhook and calendar triggers handled the remaining 32%. Your workflows collectively saved an estimated 47.3 hours this month, up from 38.8 hours last month. Failed executions decreased by 15%, primarily due to improvements in calendar authentication handling. Consider reviewing the Calendar Event Notifier workflow, which showed a higher failure rate at 12%.
          </p>
        </div>
      </div>
    </div>
  );
}
