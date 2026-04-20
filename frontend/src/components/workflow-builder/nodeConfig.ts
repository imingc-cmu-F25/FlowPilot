// Typed config shapes for each trigger / action, mirroring the backend models.

export interface TimeTriggerConfig {
  name: string;
  trigger_at: string;   // datetime-local string "YYYY-MM-DDTHH:mm"
  timezone: string;
  recurrence: {
    frequency: "minutely" | "hourly" | "daily" | "weekly" | "custom";
    interval: number;
    days_of_week: number[];   // 0=Mon … 6=Sun
    cron_expression: string;
  } | null;
}

export interface WebhookTriggerConfig {
  name: string;
  path: string;
  method: string;
  secret_ref: string;
  event_filter: string;
}

export interface CustomTriggerConfig {
  name: string;
  condition: string;
  source: string;
  description: string;
}

export interface CalendarEventTriggerConfig {
  name: string;
  calendar_id: string;
  title_contains: string;
  dedup_seconds: number;
}

export interface HttpRequestActionConfig {
  name: string;
  method: string;
  url_template: string;
  headers: { key: string; value: string }[];
  body_template: string;
}

export interface SendEmailActionConfig {
  name: string;
  to_template: string;
  subject_template: string;
  body_template: string;
  add_subject_prefix: boolean;   // prepend "[FlowPilot] "
  add_footer: boolean;            // append auto-email footer
}

export interface CalendarActionConfig {
  name: string;
  calendar_id: string;
  title_template: string;
  start_mapping: string;
  end_mapping: string;
}

export interface CalendarListUpcomingActionConfig {
  name: string;
  calendar_id: string;
  max_results: number;
  title_contains: string;
  window_hours: number;   // 0 = no cap; 24 = today only; 168 = this week
}

export type NodeConfig =
  | TimeTriggerConfig
  | WebhookTriggerConfig
  | CustomTriggerConfig
  | CalendarEventTriggerConfig
  | HttpRequestActionConfig
  | SendEmailActionConfig
  | CalendarActionConfig
  | CalendarListUpcomingActionConfig;

// ── default factories ────────────────────────────────────────────────────────

export function browserTimezone(): string {
  // Intl is available in every browser we target; fall back to UTC if the
  // runtime somehow hides it (e.g. ancient test shim).
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function defaultTimeTrigger(): TimeTriggerConfig {
  const now = new Date();
  now.setSeconds(0, 0);
  // datetime-local input expects local-time formatted "YYYY-MM-DDTHH:mm"
  const pad = (n: number) => String(n).padStart(2, "0");
  const local =
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  return {
    name: "Time Trigger",
    trigger_at: local,
    // The browser's IANA zone is the *only* timezone that matters at save-time
    // because we convert the picker's wall-clock value via `new Date(...)`,
    // which always interprets it in the browser's local zone. Storing the
    // same zone here keeps the backend's display metadata consistent with
    // the actual conversion.
    timezone: browserTimezone(),
    recurrence: null,
  };
}

export function defaultWebhookTrigger(): WebhookTriggerConfig {
  return { name: "Webhook Trigger", path: "/hooks/my-workflow", method: "POST", secret_ref: "", event_filter: "" };
}

export function defaultCustomTrigger(): CustomTriggerConfig {
  return { name: "Custom Trigger", condition: "true", source: "event_payload", description: "" };
}

export function defaultCalendarEventTrigger(): CalendarEventTriggerConfig {
  return {
    name: "New Calendar Event",
    calendar_id: "primary",
    title_contains: "",
    dedup_seconds: 60,
  };
}

export function defaultHttpRequestAction(): HttpRequestActionConfig {
  // Pre-fill a Slack / Discord / ntfy-compatible JSON payload so a demo user
  // only has to paste their webhook URL and hit Save. Method stays GET so
  // users doing simple API probes aren't surprised by a stray body — the
  // body field only surfaces in the form once they switch to POST/PUT/…
  return {
    name: "HTTP Request",
    method: "GET",
    url_template: "",
    headers: [{ key: "Content-Type", value: "application/json" }],
    body_template: '{\n  "text": "🚀 Hello from FlowPilot!"\n}',
  };
}

export function defaultSendEmailAction(): SendEmailActionConfig {
  return {
    name: "Send Email",
    to_template: "",
    subject_template: "",
    body_template: "",
    add_subject_prefix: true,
    add_footer: true,
  };
}

export function defaultCalendarAction(): CalendarActionConfig {
  return { name: "Calendar Event", calendar_id: "", title_template: "", start_mapping: "", end_mapping: "" };
}

export function defaultCalendarListUpcomingAction(): CalendarListUpcomingActionConfig {
  return {
    name: "List Upcoming Events",
    calendar_id: "primary",
    max_results: 10,
    title_contains: "",
    window_hours: 24, // default "today + rollover" — matches the most
                      // common daily-digest use case without surprising
                      // users with events from next month.
  };
}

export function defaultConfigFor(type: "trigger" | "action", category: string): NodeConfig {
  if (type === "trigger") {
    if (category === "webhook") return defaultWebhookTrigger();
    if (category === "custom") return defaultCustomTrigger();
    if (category === "calendar_event") return defaultCalendarEventTrigger();
    return defaultTimeTrigger();
  }
  if (category === "email") return defaultSendEmailAction();
  if (category === "calendar") return defaultCalendarAction();
  if (category === "calendar_list") return defaultCalendarListUpcomingAction();
  return defaultHttpRequestAction();
}
