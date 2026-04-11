import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Clock, Webhook, Calendar, Mail, Bell, Code } from "lucide-react";
import { NodePalette, type PaletteItem } from "../components/workflow-builder/NodePalette";
import { BuilderToolbar } from "../components/workflow-builder/BuilderToolbar";
import { NodePropertiesPanel } from "../components/workflow-builder/NodePropertiesPanel";
import { AIChatPanel } from "../components/workflow-builder/AIChatPanel";
import { WorkflowNodeCard } from "../components/workflow-builder/WorkflowNodeCard";

type NodeType = "trigger" | "action";

interface WorkflowNode {
  id: string;
  type: NodeType;
  category: string;
  title: string;
  icon: React.ElementType;
  config?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const triggers = [
  { category: "time", title: "Time-based Trigger", icon: Clock },
  { category: "webhook", title: "Webhook Trigger", icon: Webhook },
  { category: "calendar", title: "Google Calendar Event", icon: Calendar },
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
  const [nodes, setNodes] = useState<WorkflowNode[]>([
    {
      id: "trigger-1",
      type: "trigger",
      category: "time",
      title: "Every Day at 9:00 AM",
      icon: Clock,
      config: "Daily schedule",
    },
  ]);

  const addTrigger = (trigger: PaletteItem) => {
    const newNode: WorkflowNode = {
      id: `trigger-${Date.now()}`,
      type: "trigger",
      category: trigger.category,
      title: trigger.title,
      icon: trigger.icon,
      config: "Not configured",
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
      config: "Not configured",
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
  };

  const removeNode = (nodeId: string) => {
    setNodes(nodes.filter((n) => n.id !== nodeId));
    if (selectedNode?.id === nodeId) setSelectedNode(null);
  };

  const updateNodeProperty = (nodeId: string, property: keyof WorkflowNode, value: string) => {
    const updated = nodes.map((n) => (n.id === nodeId ? { ...n, [property]: value } : n));
    setNodes(updated);
    if (selectedNode?.id === nodeId) setSelectedNode({ ...selectedNode, [property]: value });
  };

  const sendChatMessage = () => {
    if (!chatInput.trim()) return;
    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: chatInput };
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
    <div className="flex h-[calc(100vh-4rem)]">
      <NodePalette
        triggers={triggers}
        actions={actions}
        onAddTrigger={addTrigger}
        onAddAction={addAction}
      />

      <div className="flex flex-1 flex-col overflow-hidden bg-gray-50">
        <BuilderToolbar
          workflowName={workflowName}
          isEnabled={isEnabled}
          showAIChat={showAIChat}
          onNameChange={setWorkflowName}
          onEnabledChange={setIsEnabled}
          onToggleAIChat={() => setShowAIChat(!showAIChat)}
          onRunTest={() => {}}
          onSave={() => navigate("/dashboard/workflows")}
        />

        <div className="flex-1 overflow-y-auto p-8">
          <div className="mx-auto w-full max-w-2xl space-y-4">
            {nodes.map((node, index) => (
              <div key={node.id}>
                <WorkflowNodeCard
                  title={node.title}
                  config={node.config}
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

      {selectedNode && (
        <NodePropertiesPanel
          type={selectedNode.type}
          title={selectedNode.title}
          config={selectedNode.config ?? ""}
          onTitleChange={(v) => updateNodeProperty(selectedNode.id, "title", v)}
          onConfigChange={(v) => updateNodeProperty(selectedNode.id, "config", v)}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {showAIChat && (
        <AIChatPanel
          messages={chatMessages}
          input={chatInput}
          onInputChange={setChatInput}
          onSend={sendChatMessage}
          onClose={() => setShowAIChat(false)}
        />
      )}
    </div>
  );
}
