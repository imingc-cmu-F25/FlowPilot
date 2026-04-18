import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Clock, Webhook, Mail, Bell, Code, SlidersHorizontal } from "lucide-react";
import {
  NodePalette,
  type PaletteItem,
} from "../components/workflow-builder/NodePalette";
import { BuilderToolbar } from "../components/workflow-builder/BuilderToolbar";
import { NodePropertiesPanel } from "../components/workflow-builder/NodePropertiesPanel";
import { AIChatPanel } from "../components/workflow-builder/AIChatPanel";
import { WorkflowNodeCard } from "../components/workflow-builder/WorkflowNodeCard";
import type { NodeConfig } from "../components/workflow-builder/nodeConfig";
import { defaultConfigFor } from "../components/workflow-builder/nodeConfig";
import {
  createSuggestion,
  createWorkflow,
  fetchWorkflow,
  updateWorkflow,
  type WorkflowDefinition,
} from "../lib/api";
import { getStoredUsername } from "../auth/storage";

type NodeType = "trigger" | "action";

interface WorkflowNode {
  id: string;
  type: NodeType;
  category: string;
  title: string;
  icon: React.ElementType;
  config: NodeConfig;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  workflowDraft?: WorkflowDefinition | null;
  suggestionId?: string;
}

interface TimeRecurrence {
  frequency: "minutely" | "hourly" | "daily" | "weekly" | "custom";
  interval: number;
  days_of_week: number[];
  cron_expression: string;
}

const triggers = [
  { category: "time", title: "Time-based Trigger", icon: Clock },
  { category: "webhook", title: "Webhook Trigger", icon: Webhook },
  { category: "custom", title: "Custom Trigger", icon: SlidersHorizontal },
];

const actions = [
  { category: "email", title: "Send Email", icon: Mail },
  { category: "api", title: "API Call", icon: Code },
];

const INITIAL_CHAT: ChatMessage[] = [
  {
    id: "1",
    role: "assistant",
    content:
      "Hi! I'm your AI assistant. I can help you build workflows, suggest actions, or answer questions about automation.",
  },
];

export function WorkflowBuilderPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [workflowName, setWorkflowName] = useState("New Workflow");
  const [isEnabled, setIsEnabled] = useState(true);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [showAIChat, setShowAIChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingWorkflow, setLoadingWorkflow] = useState(false);

  const toRecurrenceConfig = (value: unknown): TimeRecurrence | null => {
    if (!value || typeof value !== "object") return null;
    const v = value as Record<string, unknown>;
    const frequency = v.frequency;
    if (
      frequency !== "minutely" &&
      frequency !== "hourly" &&
      frequency !== "daily" &&
      frequency !== "weekly" &&
      frequency !== "custom"
    ) {
      return null;
    }
    return {
      frequency,
      interval: typeof v.interval === "number" ? v.interval : 1,
      days_of_week: Array.isArray(v.days_of_week)
        ? v.days_of_week.filter((d): d is number => typeof d === "number")
        : [],
      cron_expression:
        typeof v.cron_expression === "string" ? v.cron_expression : "",
    };
  };

  const toLocalDateTimeInput = (iso: string | undefined) => {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    return date.toISOString().slice(0, 16);
  };

  const mapWorkflowToNodes = (wf: WorkflowDefinition): WorkflowNode[] => {
    const result: WorkflowNode[] = [];

    if (wf.trigger.type === "time") {
      result.push({
        id: `trigger-${String((wf.trigger as { trigger_id?: string }).trigger_id ?? Date.now())}`,
        type: "trigger",
        category: "time",
        title: "Time-based Trigger",
        icon: Clock,
        config: {
          name: "Time Trigger",
          trigger_at: toLocalDateTimeInput(
            (wf.trigger as { trigger_at?: string }).trigger_at,
          ),
          timezone: String(
            (wf.trigger as { timezone?: string }).timezone ?? "UTC",
          ),
          recurrence: toRecurrenceConfig(
            (wf.trigger as { recurrence?: unknown }).recurrence,
          ),
        },
      });
    } else if (wf.trigger.type === "webhook") {
      result.push({
        id: `trigger-${String((wf.trigger as { trigger_id?: string }).trigger_id ?? Date.now())}`,
        type: "trigger",
        category: "webhook",
        title: "Webhook Trigger",
        icon: Webhook,
        config: {
          name: "Webhook Trigger",
          path: String((wf.trigger as { path?: string }).path ?? ""),
          method: String((wf.trigger as { method?: string }).method ?? "POST"),
          secret_ref: String(
            (wf.trigger as { secret_ref?: string }).secret_ref ?? "",
          ),
          event_filter: String(
            (wf.trigger as { event_filter?: string }).event_filter ?? "",
          ),
        },
      });
    } else if (wf.trigger.type === "custom") {
      result.push({
        id: `trigger-${String((wf.trigger as { trigger_id?: string }).trigger_id ?? Date.now())}`,
        type: "trigger",
        category: "custom",
        title: "Custom Trigger",
        icon: SlidersHorizontal,
        config: {
          name: "Custom Trigger",
          condition: String((wf.trigger as { condition?: string }).condition ?? ""),
          source: String((wf.trigger as { source?: string }).source ?? "event_payload"),
          description: String((wf.trigger as { description?: string }).description ?? ""),
        },
      });
    }

    const sortedSteps = [...wf.steps].sort(
      (a, b) => a.step_order - b.step_order,
    );
    for (const step of sortedSteps) {
      if (step.action_type === "send_email") {
        result.push({
          id: `action-${step.step_order}-${Date.now()}`,
          type: "action",
          category: "email",
          title: "Send Email",
          icon: Mail,
          config: {
            name: step.name,
            to_template: String(
              (step as { to_template?: string }).to_template ?? "",
            ),
            subject_template: String(
              (step as { subject_template?: string }).subject_template ?? "",
            ),
            body_template: String(
              (step as { body_template?: string }).body_template ?? "",
            ),
            add_subject_prefix: true,
            add_footer: true,
          },
        });
      } else if (step.action_type === "calendar_create_event") {
        result.push({
          id: `action-${step.step_order}-${Date.now()}`,
          type: "action",
          category: "calendar",
          title: "Calendar Event",
          icon: Bell,
          config: {
            name: step.name,
            calendar_id: String(
              (step as { calendar_id?: string }).calendar_id ?? "",
            ),
            title_template: String(
              (step as { title_template?: string }).title_template ?? "",
            ),
            start_mapping: String(
              (step as { start_mapping?: string }).start_mapping ?? "",
            ),
            end_mapping: String(
              (step as { end_mapping?: string }).end_mapping ?? "",
            ),
          },
        });
      } else {
        const headers =
          (step as { headers?: Record<string, string> }).headers ?? {};
        result.push({
          id: `action-${step.step_order}-${Date.now()}`,
          type: "action",
          category: "api",
          title: "API Call",
          icon: Code,
          config: {
            name: step.name,
            method: String((step as { method?: string }).method ?? "GET"),
            url_template: String(
              (step as { url_template?: string }).url_template ?? "",
            ),
            headers: Object.entries(headers).map(([key, value]) => ({
              key,
              value,
            })),
          },
        });
      }
    }

    return result;
  };

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    const loadWorkflow = async () => {
      setLoadingWorkflow(true);
      setSaveError(null);
      try {
        const wf = await fetchWorkflow(id);
        if (cancelled) return;
        setWorkflowName(wf.name);
        setIsEnabled(wf.enabled);
        setNodes(mapWorkflowToNodes(wf));
      } catch (e) {
        if (cancelled) return;
        setSaveError(
          e instanceof Error ? e.message : "Failed to load workflow.",
        );
      } finally {
        if (!cancelled) setLoadingWorkflow(false);
      }
    };

    void loadWorkflow();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const addTrigger = (trigger: PaletteItem) => {
    const newNode: WorkflowNode = {
      id: `trigger-${Date.now()}`,
      type: "trigger",
      category: trigger.category,
      title: trigger.title,
      icon: trigger.icon,
      config: defaultConfigFor("trigger", trigger.category),
    };
    const existingIndex = nodes.findIndex((n) => n.type === "trigger");
    if (existingIndex !== -1) {
      const updated = [...nodes];
      updated[existingIndex] = newNode;
      setNodes(updated);
    } else {
      setNodes([newNode, ...nodes]);
    }
    setSelectedNode(newNode);
  };

  const addAction = (action: PaletteItem) => {
    const newNode: WorkflowNode = {
      id: `action-${Date.now()}`,
      type: "action",
      category: action.category,
      title: action.title,
      icon: action.icon,
      config: defaultConfigFor("action", action.category),
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
  };

  const removeNode = (nodeId: string) => {
    setNodes(nodes.filter((n) => n.id !== nodeId));
    if (selectedNode?.id === nodeId) setSelectedNode(null);
  };

  const confirmNodeConfig = (nodeId: string, config: NodeConfig) => {
    const updated = nodes.map((n) => (n.id === nodeId ? { ...n, config } : n));
    setNodes(updated);
    setSelectedNode(null);
  };

  const handleSave = async () => {
    setSaveError(null);
    const triggerNode = nodes.find((n) => n.type === "trigger");
    const actionNodes = nodes.filter((n) => n.type === "action");
    if (!triggerNode) {
      setSaveError("Add a trigger before saving.");
      return;
    }
    if (actionNodes.length === 0) {
      setSaveError("Add at least one action before saving.");
      return;
    }

    const triggerCfg = triggerNode.config as unknown as Record<string, unknown>;
    const trigger =
      triggerNode.category === "time"
        ? {
            type: "time" as const,
            parameters: {
              trigger_at: (() => {
                const raw = String(triggerCfg.trigger_at ?? "");
                return raw.includes("+") || raw.endsWith("Z")
                  ? raw
                  : raw + ":00+00:00";
              })(),
              timezone: triggerCfg.timezone ?? "UTC",
              recurrence: triggerCfg.recurrence ?? null,
            },
          }
        : triggerNode.category === "custom"
          ? {
              type: "custom" as const,
              parameters: {
                condition: String(triggerCfg.condition ?? ""),
                source: String(triggerCfg.source ?? "event_payload"),
                description: String(triggerCfg.description ?? ""),
              },
            }
          : {
              type: "webhook" as const,
              parameters: {
                path: triggerCfg.path,
                method: triggerCfg.method ?? "POST",
                secret_ref: triggerCfg.secret_ref ?? "",
                event_filter: triggerCfg.event_filter ?? "",
              },
            };

    const steps = actionNodes.map((n, i) => {
      const cfg = n.config as unknown as Record<string, unknown>;
      const base = { name: String(cfg.name ?? n.title), step_order: i };
      if (n.category === "email") {
        return {
          action_type: "send_email" as const,
          ...base,
          parameters: {
            to_template: cfg.to_template,
            subject_template: cfg.subject_template,
            body_template: cfg.body_template,
          },
        };
      }
      if (n.category === "calendar") {
        return {
          action_type: "calendar_create_event" as const,
          ...base,
          parameters: {
            calendar_id: cfg.calendar_id,
            title_template: cfg.title_template,
            start_mapping: cfg.start_mapping,
            end_mapping: cfg.end_mapping,
          },
        };
      }
      return {
        action_type: "http_request" as const,
        ...base,
        parameters: {
          method: cfg.method ?? "GET",
          url_template: cfg.url_template ?? "",
          headers: Object.fromEntries(
            ((cfg.headers as { key: string; value: string }[]) ?? []).map(
              (h) => [h.key, h.value],
            ),
          ),
        },
      };
    });

    setSaving(true);
    try {
      if (id) {
        await updateWorkflow(id, {
          name: workflowName,
          enabled: isEnabled,
          trigger,
          steps,
        });
      } else {
        await createWorkflow({
          owner_name: getStoredUsername() ?? "alice",
          name: workflowName,
          enabled: isEnabled,
          trigger,
          steps,
        });
      }
      navigate("/dashboard/workflows");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save workflow.");
    } finally {
      setSaving(false);
    }
  };

  const sendChatMessage = async () => {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await createSuggestion({
        raw_text: text,
        user_name: getStoredUsername() ?? null,
      });
      const assistantMsg: ChatMessage = {
        id: res.id,
        role: "assistant",
        content: res.content,
        workflowDraft: res.workflow_draft,
        suggestionId: res.id,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-err`,
          role: "assistant",
          content:
            e instanceof Error
              ? `Sorry, I couldn't generate a suggestion: ${e.message}`
              : "Sorry, I couldn't generate a suggestion.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const applyDraftToCanvas = (draft: WorkflowDefinition) => {
    if (draft.name) setWorkflowName(draft.name);
    setNodes(mapWorkflowToNodes(draft));
    setSelectedNode(null);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      <NodePalette
        triggers={triggers}
        actions={actions}
        onAddTrigger={addTrigger}
        onAddAction={addAction}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-gray-50">
        <BuilderToolbar
          workflowName={workflowName}
          isEnabled={isEnabled}
          showAIChat={showAIChat}
          onNameChange={setWorkflowName}
          onEnabledChange={setIsEnabled}
          onToggleAIChat={() => setShowAIChat(!showAIChat)}
          onSave={handleSave}
          saving={saving}
          onDiscard={() => navigate("/dashboard/workflows")}
        />

        {loadingWorkflow && (
          <div className="border-b border-blue-200 bg-blue-50 px-6 py-2 text-sm text-blue-700">
            Loading workflow...
          </div>
        )}

        {saveError && (
          <div className="border-b border-red-200 bg-red-50 px-6 py-2 text-sm text-red-700">
            {saveError}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
          <div className="mx-auto w-full max-w-2xl space-y-4">
            {nodes.map((node, index) => (
              <div key={node.id}>
                <WorkflowNodeCard
                  title={node.title}
                  config={(node.config as { name?: string }).name}
                  type={node.type}
                  icon={node.icon}
                  selected={selectedNode?.id === node.id}
                  onClick={() => setSelectedNode(node)}
                  onRemove={() => removeNode(node.id)}
                />
                {index < nodes.length - 1 && (
                  <div className="flex justify-center py-2">
                    <div className="h-8 w-0.5 bg-gray-300" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* On small screens: panels slide over canvas as a fixed overlay.
          On md+: panels sit inline as a sidebar. */}
      {selectedNode && (
        <>
          {/* Mobile backdrop */}
          <div
            className="fixed inset-0 z-20 bg-black/20 md:hidden"
            onClick={() => setSelectedNode(null)}
          />
          <div className="fixed inset-y-0 right-0 z-30 flex h-full md:relative md:inset-auto md:z-auto">
            <NodePropertiesPanel
              key={selectedNode.id}
              type={selectedNode.type}
              category={selectedNode.category}
              config={selectedNode.config}
              onConfirm={(config) => confirmNodeConfig(selectedNode.id, config)}
              onRemove={() => removeNode(selectedNode.id)}
            />
          </div>
        </>
      )}

      {showAIChat && !selectedNode && (
        <>
          <div
            className="fixed inset-0 z-20 bg-black/20 md:hidden"
            onClick={() => setShowAIChat(false)}
          />
          <div className="fixed inset-y-0 right-0 z-30 md:relative md:inset-auto md:z-auto">
            <AIChatPanel
              messages={chatMessages}
              input={chatInput}
              onInputChange={setChatInput}
              onSend={sendChatMessage}
              onClose={() => setShowAIChat(false)}
              onApplyDraft={applyDraftToCanvas}
              loading={chatLoading}
            />
          </div>
        </>
      )}

      {/* On md+ show AI panel alongside properties if both open */}
      {showAIChat && selectedNode && (
        <div className="hidden md:flex">
          <AIChatPanel
            messages={chatMessages}
            input={chatInput}
            onInputChange={setChatInput}
            onSend={sendChatMessage}
            onClose={() => setShowAIChat(false)}
          />
        </div>
      )}
    </div>
  );
}
