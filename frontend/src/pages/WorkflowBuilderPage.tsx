import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Clock, Webhook, Mail, Bell, Code } from "lucide-react";
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
import { createWorkflow } from "../lib/api";
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
}

const triggers = [
  { category: "time", title: "Time-based Trigger", icon: Clock },
  { category: "webhook", title: "Webhook Trigger", icon: Webhook },
];

const actions = [
  { category: "email", title: "Send Email", icon: Mail },
  { category: "notification", title: "Send Notification", icon: Bell },
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
  const { id: _id } = useParams();
  const navigate = useNavigate();

  const [workflowName, setWorkflowName] = useState("New Workflow");
  const [isEnabled, setIsEnabled] = useState(true);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [showAIChat, setShowAIChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT);
  const [chatInput, setChatInput] = useState("");
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

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
    if (!triggerNode) { setSaveError("Add a trigger before saving."); return; }
    if (actionNodes.length === 0) { setSaveError("Add at least one action before saving."); return; }

    const triggerCfg = triggerNode.config as unknown as Record<string, unknown>;
    const trigger = triggerNode.category === "time"
      ? {
          type: "time" as const,
          parameters: {
            trigger_at: (() => {
              const raw = String(triggerCfg.trigger_at ?? "");
              // datetime-local gives "YYYY-MM-DDTHH:mm"; make it a valid UTC ISO string
              return raw.includes("+") || raw.endsWith("Z") ? raw : raw + ":00+00:00";
            })(),
            timezone: triggerCfg.timezone ?? "UTC",
            recurrence: triggerCfg.recurrence ?? null,
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
        return { action_type: "send_email" as const, ...base, parameters: {
          to_template: cfg.to_template, subject_template: cfg.subject_template, body_template: cfg.body_template,
        }};
      }
      if (n.category === "calendar") {
        return { action_type: "calendar_create_event" as const, ...base, parameters: {
          calendar_id: cfg.calendar_id, title_template: cfg.title_template,
          start_mapping: cfg.start_mapping, end_mapping: cfg.end_mapping,
        }};
      }
      return { action_type: "http_request" as const, ...base, parameters: {
        method: cfg.method ?? "GET", url_template: cfg.url_template ?? "",
        headers: Object.fromEntries(
          ((cfg.headers as { key: string; value: string }[]) ?? []).map((h) => [h.key, h.value])
        ),
      }};
    });

    setSaving(true);
    try {
      await createWorkflow({
        owner_name: getStoredUsername() ?? "alice",
        name: workflowName,
        enabled: isEnabled,
        trigger,
        steps,
      });
      navigate("/dashboard/workflows");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save workflow.");
    } finally {
      setSaving(false);
    }
  };

  const sendChatMessage = () => {
    if (!chatInput.trim()) return;
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: chatInput,
    };
    const assistantMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content:
        "I understand. Let me help you with that. (This is a demo response - in a real implementation, this would connect to an AI service.)",
    };
    setChatMessages([...chatMessages, userMsg, assistantMsg]);
    setChatInput("");
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
