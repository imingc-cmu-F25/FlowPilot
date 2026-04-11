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

export interface HttpRequestActionConfig {
  name: string;
  method: string;
  url_template: string;
  headers: { key: string; value: string }[];
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

export type NodeConfig =
  | TimeTriggerConfig
  | WebhookTriggerConfig
  | HttpRequestActionConfig
  | SendEmailActionConfig
  | CalendarActionConfig;

// ── default factories ────────────────────────────────────────────────────────

export function defaultTimeTrigger(): TimeTriggerConfig {
  const now = new Date();
  now.setSeconds(0, 0);
  return {
    name: "Time Trigger",
    trigger_at: now.toISOString().slice(0, 16),
    timezone: "UTC",
    recurrence: null,
  };
}

export function defaultWebhookTrigger(): WebhookTriggerConfig {
  return { name: "Webhook Trigger", path: "/hooks/my-workflow", method: "POST", secret_ref: "", event_filter: "" };
}

export function defaultHttpRequestAction(): HttpRequestActionConfig {
  return { name: "HTTP Request", method: "GET", url_template: "", headers: [] };
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

export function defaultConfigFor(type: "trigger" | "action", category: string): NodeConfig {
  if (type === "trigger") {
    return category === "webhook" ? defaultWebhookTrigger() : defaultTimeTrigger();
  }
  if (category === "email") return defaultSendEmailAction();
  if (category === "calendar") return defaultCalendarAction();
  return defaultHttpRequestAction();
}
