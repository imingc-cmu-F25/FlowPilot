import type { SendEmailActionConfig } from "../nodeConfig";

const SUBJECT_PREFIX = "[FlowPilot] ";
const FOOTER = `\n\n---\nThis email was automatically sent by FlowPilot.\nTo manage your workflows, visit your FlowPilot dashboard.`;

interface Props {
  config: SendEmailActionConfig;
  onChange: (config: SendEmailActionConfig) => void;
}

export function SendEmailActionForm({ config, onChange }: Props) {
  function set<K extends keyof SendEmailActionConfig>(key: K, value: SendEmailActionConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  function togglePrefix(enabled: boolean) {
    let subject = config.subject_template;
    if (enabled && !subject.startsWith(SUBJECT_PREFIX)) {
      subject = SUBJECT_PREFIX + subject;
    } else if (!enabled && subject.startsWith(SUBJECT_PREFIX)) {
      subject = subject.slice(SUBJECT_PREFIX.length);
    }
    onChange({ ...config, add_subject_prefix: enabled, subject_template: subject });
  }

  function toggleFooter(enabled: boolean) {
    let body = config.body_template;
    if (enabled && !body.endsWith(FOOTER)) {
      body = body + FOOTER;
    } else if (!enabled && body.endsWith(FOOTER)) {
      body = body.slice(0, body.length - FOOTER.length);
    }
    onChange({ ...config, add_footer: enabled, body_template: body });
  }

  // Keep prefix/footer in sync when user edits the raw fields directly
  function handleSubjectChange(value: string) {
    const hasPrefix = value.startsWith(SUBJECT_PREFIX);
    onChange({ ...config, subject_template: value, add_subject_prefix: hasPrefix });
  }

  function handleBodyChange(value: string) {
    const hasFooter = value.endsWith(FOOTER);
    onChange({ ...config, body_template: value, add_footer: hasFooter });
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
          placeholder="E.g. Notify team"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* To */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          To <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.to_template}
          onChange={(e) => set("to_template", e.target.value)}
          placeholder="team@example.com or {{user.email}}"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Subject */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            Subject <span className="text-red-500">*</span>
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={config.add_subject_prefix ?? false}
              onChange={(e) => togglePrefix(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Add <code className="rounded bg-gray-100 px-1 text-blue-700">[FlowPilot]</code> prefix
          </label>
        </div>
        <input
          type="text"
          value={config.subject_template}
          onChange={(e) => handleSubjectChange(e.target.value)}
          placeholder="Your report for {{date}}"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Body */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            Body <span className="text-red-500">*</span>
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={config.add_footer ?? false}
              onChange={(e) => toggleFooter(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Auto-email footer
          </label>
        </div>
        <textarea
          rows={7}
          value={config.body_template}
          onChange={(e) => handleBodyChange(e.target.value)}
          placeholder={"Hi {{user.name}},\n\nHere is your daily summary:\n{{summary}}"}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {config.add_footer && (
          <p className="mt-1 text-xs text-gray-400">
            Footer preview:{" "}
            <span className="italic">
              "This email was automatically sent by FlowPilot…"
            </span>
          </p>
        )}
      </div>

      <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-xs text-gray-600">
        <p className="mb-1 font-medium text-gray-700">Template variables</p>
        <p className="mb-2">
          Use{" "}
          <code className="rounded bg-white px-1 font-mono">
            {"{{path.to.value}}"}
          </code>{" "}
          to inject values from the previous step. Most useful:
        </p>
        <dl className="space-y-2">
          <div>
            <dt>
              <code className="inline-block max-w-full break-all rounded bg-white px-1 py-0.5 font-mono">
                {"{{previous_output.agenda_text}}"}
              </code>
            </dt>
            <dd className="mt-0.5 text-gray-500">
              After a "List Upcoming Events" step — a ready-to-paste bullet
              list of meetings.
            </dd>
          </div>
          <div>
            <dt>
              <code className="inline-block max-w-full break-all rounded bg-white px-1 py-0.5 font-mono">
                {"{{previous_output.count}}"}
              </code>
            </dt>
            <dd className="mt-0.5 text-gray-500">
              Integer count of items from the previous step.
            </dd>
          </div>
          <div>
            <dt>
              <code className="inline-block max-w-full break-all rounded bg-white px-1 py-0.5 font-mono">
                {"{{previous_output.status_code}}"}
              </code>
            </dt>
            <dd className="mt-0.5 text-gray-500">
              After an HTTP Request step.
            </dd>
          </div>
        </dl>
        <p className="mt-2 text-[11px] text-gray-500">
          Missing paths render as empty strings — no error at runtime.
        </p>
      </div>
    </div>
  );
}
