import { useMemo, useState } from "react";
import { API_BASE } from "../../../lib/api";
import type { WebhookTriggerConfig } from "../nodeConfig";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

interface Props {
  config: WebhookTriggerConfig;
  onChange: (config: WebhookTriggerConfig) => void;
}

function publicBase(): string {
  // API_BASE is "http://127.0.0.1:8000/api" in dev, or whatever
  // VITE_API_BASE_URL is set to in a deployed build. We show it
  // verbatim — if the value is localhost, the user *knows* they
  // need to tunnel it (e.g. via ngrok) for Slack to reach it.
  if (API_BASE) return API_BASE;
  // Fall back to same-origin when API_BASE is empty (prod with
  // /api served from the same host as the UI).
  if (typeof window !== "undefined") return `${window.location.origin}/api`;
  return "/api";
}

export function WebhookTriggerForm({ config, onChange }: Props) {
  const [copied, setCopied] = useState(false);

  function set<K extends keyof WebhookTriggerConfig>(
    key: K,
    value: WebhookTriggerConfig[K],
  ) {
    onChange({ ...config, [key]: value });
  }

  const fullUrl = useMemo(() => {
    const base = publicBase().replace(/\/$/, "");
    const path = config.path.startsWith("/") ? config.path : `/${config.path}`;
    return `${base}${path}`;
  }, [config.path]);

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  const usingSlack = config.secret_ref.startsWith("slack:");

  return (
    <div className="space-y-4">
      {/* What is this? */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
        <p className="font-medium">What this trigger does</p>
        <p className="mt-1">
          Starts the workflow whenever an HTTP request hits the URL below.
          The request&#39;s body, headers, and query string are passed into
          step 1 as <code className="rounded bg-white px-1">{"{{previous_output}}"}</code>,
          so downstream actions (e.g. <em>Create Calendar Event</em>,
          <em> Send Email</em>) can use values from the caller.
        </p>
      </div>

      {/* Name */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Slack /block command"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Path */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Path <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.path}
          onChange={(e) => set("path", e.target.value)}
          placeholder="/hooks/my-workflow"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">Must start with /</p>
      </div>

      {/* Method */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">HTTP method</label>
        <select
          value={config.method}
          onChange={(e) => set("method", e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {HTTP_METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Public URL preview */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
        <p className="text-xs font-medium text-gray-600">Webhook URL</p>
        <div className="mt-1 flex items-center gap-2">
          <code className="flex-1 truncate rounded bg-white px-2 py-1 font-mono text-xs text-gray-800">
            {fullUrl}
          </code>
          <button
            type="button"
            onClick={copyUrl}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Paste this into Slack&#39;s slash command setup, a cURL call, or
          any external service. If the host is <code>localhost</code>,
          expose it via <code>ngrok</code> (or deploy) before Slack can
          reach it.
        </p>
      </div>

      {/* Secret ref */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Authentication
          <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="text"
          value={config.secret_ref}
          onChange={(e) => set("secret_ref", e.target.value)}
          placeholder="slack:xxxxxSLACK_SIGNING_SECRETxxxxx"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <div className="mt-1 space-y-1 text-xs text-gray-500">
          <p>
            <span className="font-medium text-gray-700">Empty</span> — no auth,
            any caller can fire the workflow (fine for local testing).
          </p>
          <p>
            <code className="rounded bg-gray-100 px-1">slack:&lt;signing-secret&gt;</code>
            {" "}— verify Slack&#39;s <code>X-Slack-Signature</code> header
            using Slack&#39;s v0 scheme. Grab the signing secret from{" "}
            <em>Slack app → Basic Information → Signing Secret</em>.
          </p>
          <p>
            <span className="font-medium text-gray-700">Any other value</span>{" "}
            — treated as a shared HMAC secret. Caller must send{" "}
            <code>X-Signature-SHA256: sha256=&lt;hex&gt;</code> over the raw
            body.
          </p>
        </div>
        {usingSlack && (
          <div className="mt-2 rounded border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-900">
            Slack mode detected. Requests older than 5 minutes or with a
            bad signature are rejected with <code>401</code>.
          </div>
        )}
      </div>

      {/* Event filter */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Event filter
          <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="text"
          value={config.event_filter}
          onChange={(e) => set("event_filter", e.target.value)}
          placeholder="push"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Matches against the <code>X-Event-Type</code> header; empty means
          accept any event. Useful for services that multiplex many event
          kinds onto a single URL (GitHub, Linear, …).
        </p>
      </div>

      {/* Available template variables */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
        <p className="text-xs font-medium text-gray-700">
          Available as{" "}
          <code className="rounded bg-white px-1">{"{{trigger.*}}"}</code> in{" "}
          <em>every</em> step, and as{" "}
          <code className="rounded bg-white px-1">{"{{previous_output.*}}"}</code>{" "}
          in the first step for backwards compatibility. Use{" "}
          <code className="rounded bg-white px-1">{"{{trigger.*}}"}</code> when
          you insert an intermediate step (HTTP call, List Upcoming Events,
          …) and still need to reach Slack / GitHub payload fields.
        </p>
        <ul className="mt-2 space-y-2 text-xs text-gray-600">
          {[
            {
              key: "{{trigger.body}}",
              desc: "parsed JSON / form body as an object",
            },
            {
              key: "{{trigger.body.text}}",
              desc: "Slack slash command — what the user typed after the command",
            },
            {
              key: "{{trigger.parsed.subject}}",
              desc: "Slack text with the first duration (30m / 1h / 2 hours) stripped — ideal for event titles",
            },
            {
              key: "{{trigger.parsed.duration}}",
              desc: "normalised duration token (30m / 2h / 1d). Defaults to 30m. Drop into Create Calendar Event's End field as start+{{trigger.parsed.duration}}",
            },
            {
              key: "{{trigger.parsed.duration_minutes}}",
              desc: "same duration as an integer (e.g. 30). Handy for email bodies",
            },
            {
              key: "{{trigger.body.user_name}}",
              desc: "Slack slash command — the caller's Slack handle",
            },
            {
              key: "{{trigger.body.command}}",
              desc: "Slack slash command — the command string (e.g. /block)",
            },
            {
              key: "{{trigger.headers.x-github-event}}",
              desc: "any header (keys are lower-cased)",
            },
            {
              key: "{{trigger.query.foo}}",
              desc: "any URL query parameter",
            },
            {
              key: "{{trigger.body_text}}",
              desc: "raw body as a string (capped at 64 KB)",
            },
          ].map((v) => (
            <li key={v.key} className="flex flex-col gap-0.5">
              <code className="block w-full break-all rounded bg-white px-1 py-0.5 font-mono text-[11px] text-gray-800">
                {v.key}
              </code>
              <span className="text-gray-500">— {v.desc}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Slack demo recipe */}
      <details className="rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700">
        <summary className="cursor-pointer font-medium text-gray-800">
          Slack slash command: end-to-end setup
        </summary>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>
            In Slack, create (or open) an app at{" "}
            <a
              href="https://api.slack.com/apps"
              className="text-blue-600 underline"
              target="_blank"
              rel="noreferrer"
            >
              api.slack.com/apps
            </a>
            .
          </li>
          <li>
            Under <em>Slash Commands</em>, create one (e.g. <code>/block</code>)
            and paste the Webhook URL above as its <em>Request URL</em>.
          </li>
          <li>
            Under <em>Basic Information → Signing Secret</em>, copy the
            signing secret and paste it above as{" "}
            <code>slack:&lt;secret&gt;</code>.
          </li>
          <li>
            Install / reinstall the app in your workspace, then run the
            slash command — the FlowPilot workflow fires and the slash
            command reply ends up in the channel as an ephemeral message.
          </li>
        </ol>
      </details>

      {/* cURL demo */}
      <details className="rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700">
        <summary className="cursor-pointer font-medium text-gray-800">
          Quick test with cURL (no signature)
        </summary>
        <pre className="mt-2 overflow-x-auto rounded bg-gray-900 p-2 font-mono text-[11px] text-gray-100">
{`curl -X ${config.method} "${fullUrl}" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "review the spec", "user_name": "alice"}'`}
        </pre>
        <p className="mt-2 text-xs text-gray-500">
          Leave <em>Authentication</em> empty while testing so the call
          isn&#39;t rejected. Add <code>slack:…</code> once the Slack side
          is wired up.
        </p>
      </details>
    </div>
  );
}
