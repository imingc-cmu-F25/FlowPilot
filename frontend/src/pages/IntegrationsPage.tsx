import { Link } from "react-router";
import { getStoredUsername } from "../auth/storage";
import { ConnectionsCard } from "../components/profile/ConnectionsCard";

export function IntegrationsPage() {
  const username = getStoredUsername();
  if (!username) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-8">
        <p className="text-gray-700">
          Sign in to manage integrations.{" "}
          <Link
            to="/login"
            className="font-medium text-blue-600 hover:text-blue-700"
          >
            Sign in
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Integrations</h1>
        <p className="mt-1 text-sm text-gray-600">
          Link outside services so your workflows can read from and write to
          them. Tokens stay on the server and you can disconnect at any time.
        </p>
      </div>

      <div className="mb-6 rounded-lg border border-blue-100 bg-blue-50 p-5 text-sm text-blue-900">
        <p className="mb-2 font-semibold">
          Google Calendar already sends reminders — what does FlowPilot add?
        </p>
        <ul className="list-disc space-y-1 pl-5 leading-relaxed">
          <li>
            <span className="font-medium">Custom responses.</span> Google gives
            you a fixed popup/email N minutes before an event. FlowPilot lets
            you run any action chain — Slack message, templated email, HTTP
            call, or several of them in order.
          </li>
          <li>
            <span className="font-medium">Filtered triggers.</span> Only react
            to events whose title contains{" "}
            <code className="rounded bg-blue-100 px-1">interview</code>,{" "}
            <code className="rounded bg-blue-100 px-1">1:1</code>, etc. — not
            every meeting on your calendar.
          </li>
          <li>
            <span className="font-medium">Digests &amp; agendas.</span> Google
            reminds you per event. FlowPilot can aggregate: "every weekday 8am,
            email me today's meetings with prep notes" via the{" "}
            <em>List Upcoming Events</em> action.
          </li>
          <li>
            <span className="font-medium">Calendar as data.</span> Use events
            as input to bigger workflows (CRM updates, stand-up summaries,
            meeting-prep docs), not just standalone reminders.
          </li>
        </ul>
        <p className="mt-3 text-xs text-blue-800/80">
          Once connected, open the workflow builder and you'll find the{" "}
          <em>New Calendar Event</em> trigger and the{" "}
          <em>List Upcoming Events</em> action in the palette.
        </p>
      </div>

      <ConnectionsCard />
    </div>
  );
}
