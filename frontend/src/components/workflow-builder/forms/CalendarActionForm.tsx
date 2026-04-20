import type { CalendarActionConfig } from "../nodeConfig";
import {
  Chip,
  HintDL,
  HintFootnote,
  HintIntro,
  HintItem,
  HintPanel,
  HintSection,
} from "./hintPanel";

interface Props {
  config: CalendarActionConfig;
  onChange: (config: CalendarActionConfig) => void;
}

// Historical note: the start/end fields are named *_mapping and used to
// show JSONPath-style placeholders (e.g. "$.steps[0].output.start_time"),
// but the step runner only ever runs them through the project's {{...}}
// templating engine — see backend/app/execution/step_runner.py and
// backend/app/execution/templating.py. That mismatch silently produced
// broken events at runtime. The placeholders and hints below now reflect
// what the backend actually accepts.
//
// Styling intent: share HintPanel/Section/Item with the other action
// forms so Create Calendar Event, List Upcoming Events and Send Email
// all feel like the same product. The long variable reference lives in
// a collapsed panel so the form stays compact by default.
export function CalendarActionForm({ config, onChange }: Props) {
  function set<K extends keyof CalendarActionConfig>(key: K, value: CalendarActionConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Book focus block"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Calendar ID */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Calendar ID <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.calendar_id}
          onChange={(e) => set("calendar_id", e.target.value)}
          placeholder="primary"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Use <code className="rounded bg-gray-100 px-1 font-mono">primary</code>{" "}
          for your default Google Calendar, or a shared calendar's email
          address.
        </p>
      </div>

      {/* Event title */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Event title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.title_template}
          onChange={(e) => set("title_template", e.target.value)}
          placeholder="Focus: {{trigger.parsed.subject}}"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Start time */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Start time <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.start_mapping}
          onChange={(e) => set("start_mapping", e.target.value)}
          placeholder="now+5m"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* End time */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          End time <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.end_mapping}
          onChange={(e) => set("end_mapping", e.target.value)}
          placeholder="start+{{trigger.parsed.duration}}"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <HintPanel summary="Template variables & time tokens">
        <HintIntro>
          Start / End accept three shapes: a relative token (<Chip>now</Chip>{" "}
          <Chip>now+30m</Chip> <Chip>start+30m</Chip>), an ISO-8601 string,
          or a <Chip>{"{{…}}"}</Chip> template that resolves to one. Title
          supports <Chip>{"{{…}}"}</Chip> too.
        </HintIntro>

        <HintSection label="Relative time tokens">
          <HintDL>
            <HintItem codes={["now", "now+5m", "now+2h", "now-15m"]}>
              Offset from the moment the step runs. Units:{" "}
              <code className="font-mono">m</code>,{" "}
              <code className="font-mono">h</code>,{" "}
              <code className="font-mono">d</code>.
            </HintItem>
            <HintItem codes={["start+30m"]} note="End field only">
              Offset from the resolved Start — ideal for fixed-length focus
              blocks.
            </HintItem>
          </HintDL>
        </HintSection>

        <HintSection label="Slack webhook variables">
          <HintIntro>
            <Chip>{"{{trigger.*}}"}</Chip> is the original webhook payload
            and is visible to every step.
          </HintIntro>
          <HintDL>
            <HintItem codes={["{{trigger.parsed.subject}}"]}>
              Slack text with the duration stripped — e.g.{" "}
              <code className="font-mono">/block focus 30min</code> →{" "}
              <code className="font-mono">focus</code>.
            </HintItem>
            <HintItem codes={["{{trigger.parsed.duration}}"]}>
              Normalised token ( <code className="font-mono">30m</code>,{" "}
              <code className="font-mono">2h</code>,{" "}
              <code className="font-mono">1d</code>). Defaults to{" "}
              <code className="font-mono">30m</code> when no duration was
              typed. Drop into End as{" "}
              <code className="font-mono break-all">
                {"start+{{trigger.parsed.duration}}"}
              </code>
              .
            </HintItem>
            <HintItem codes={["{{trigger.parsed.duration_minutes}}"]}>
              Same duration as an integer — useful for email bodies
              (<em>"Focus block: 30 minutes"</em>).
            </HintItem>
            <HintItem
              codes={["{{trigger.body.text}}", "{{trigger.body.user_name}}"]}
            >
              Raw Slack text and caller's handle.
            </HintItem>
          </HintDL>
        </HintSection>

        <HintSection label="After a List Upcoming Events step">
          <HintDL>
            <HintItem
              codes={[
                "{{previous_output.events.0.start}}",
                "{{previous_output.events.0.end}}",
              ]}
            >
              ISO-8601 timestamps from the next upcoming event — paste
              directly into Start / End.
            </HintItem>
          </HintDL>
        </HintSection>

        <HintFootnote>
          If Google OAuth is configured and the owner has linked their
          account under <em>Dashboard → Connections</em>, the event lands
          on the real calendar; otherwise FlowPilot returns a mock event
          so the workflow still completes end-to-end.
        </HintFootnote>
      </HintPanel>
    </div>
  );
}
