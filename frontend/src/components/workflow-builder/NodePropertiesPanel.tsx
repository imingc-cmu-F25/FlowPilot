import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import type {
  NodeConfig,
  TimeTriggerConfig,
  WebhookTriggerConfig,
  CustomTriggerConfig,
  CalendarEventTriggerConfig,
  HttpRequestActionConfig,
  SendEmailActionConfig,
  CalendarActionConfig,
  CalendarListUpcomingActionConfig,
} from "./nodeConfig";
import { TimeTriggerForm } from "./forms/TimeTriggerForm";
import { WebhookTriggerForm } from "./forms/WebhookTriggerForm";
import { CustomTriggerForm } from "./forms/CustomTriggerForm";
import { CalendarEventTriggerForm } from "./forms/CalendarEventTriggerForm";
import { HttpRequestActionForm } from "./forms/HttpRequestActionForm";
import { SendEmailActionForm } from "./forms/SendEmailActionForm";
import { CalendarActionForm } from "./forms/CalendarActionForm";
import { CalendarListUpcomingForm } from "./forms/CalendarListUpcomingForm";

interface NodePropertiesPanelProps {
  type: "trigger" | "action";
  category: string;
  config: NodeConfig;
  onConfirm: (config: NodeConfig) => void;
  onRemove: () => void;
}

const SECTION_LABELS: Record<string, string> = {
  time: "Time-based Trigger",
  webhook: "Webhook Trigger",
  custom: "Custom Trigger",
  calendar_event: "New Calendar Event",
  calendar: "Create Calendar Event",
  calendar_list: "List Upcoming Events",
  email: "Send Email",
  api: "HTTP Request",
  notification: "HTTP Request",
};

export function NodePropertiesPanel({
  type,
  category,
  config,
  onConfirm,
  onRemove,
}: NodePropertiesPanelProps) {
  const [draft, setDraft] = useState<NodeConfig>(config);
  const [confirming, setConfirming] = useState(false);

  const label = SECTION_LABELS[category] ?? (type === "trigger" ? "Trigger" : "Action");

  function handleConfirm() {
    onConfirm(draft);
  }

  function handleDiscard() {
    setConfirming(true);
  }

  function handleDiscardConfirmed() {
    onRemove();
  }

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden border-l border-gray-200 bg-white sm:w-80 md:w-80">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 px-6 py-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            {type === "trigger" ? "Trigger" : "Action"}
          </p>
          <h3 className="text-base font-semibold text-gray-900">{label}</h3>
        </div>
        <button
          onClick={handleDiscard}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Discard and close"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Form — scrollable */}
      <div className="flex-1 overflow-y-auto p-6">
        {type === "trigger" && category === "webhook" ? (
          <WebhookTriggerForm
            config={draft as WebhookTriggerConfig}
            onChange={setDraft}
          />
        ) : type === "trigger" && category === "custom" ? (
          <CustomTriggerForm
            config={draft as CustomTriggerConfig}
            onChange={setDraft}
          />
        ) : type === "trigger" && category === "calendar_event" ? (
          <CalendarEventTriggerForm
            config={draft as CalendarEventTriggerConfig}
            onChange={setDraft}
          />
        ) : type === "trigger" && category === "time" ? (
          <TimeTriggerForm
            config={draft as TimeTriggerConfig}
            onChange={setDraft}
          />
        ) : category === "email" ? (
          <SendEmailActionForm
            config={draft as SendEmailActionConfig}
            onChange={setDraft}
          />
        ) : category === "calendar" ? (
          <CalendarActionForm
            config={draft as CalendarActionConfig}
            onChange={setDraft}
          />
        ) : category === "calendar_list" ? (
          <CalendarListUpcomingForm
            config={draft as CalendarListUpcomingActionConfig}
            onChange={setDraft}
          />
        ) : (
          <HttpRequestActionForm
            config={draft as HttpRequestActionConfig}
            onChange={setDraft}
          />
        )}
      </div>

      {/* Action buttons */}
      <div className="shrink-0 border-t border-gray-200 px-6 py-4">
        <div className="flex gap-3">
          <button
            onClick={handleDiscard}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            Discard
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Confirm
          </button>
        </div>
      </div>

      {/* Discard confirmation overlay */}
      {confirming && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="mx-4 rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
            <div className="mb-3 flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <span className="text-sm font-semibold">Discard changes?</span>
            </div>
            <p className="mb-5 text-sm text-gray-600">
              This {type} will be removed from the workflow and your changes won't be saved.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirming(false)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Keep editing
              </button>
              <button
                onClick={handleDiscardConfirmed}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
