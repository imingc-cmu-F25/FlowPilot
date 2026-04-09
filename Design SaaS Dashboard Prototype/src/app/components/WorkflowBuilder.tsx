import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Save, Play, Clock, Webhook, Calendar, Mail, Bell, Code, Sparkles, GripVertical, Trash2, X } from "lucide-react";

type NodeType = "trigger" | "action";

interface Node {
  id: string;
  type: NodeType;
  category: string;
  title: string;
  icon: any;
  config?: string;
}

export function WorkflowBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workflowName, setWorkflowName] = useState("New Workflow");
  const [isEnabled, setIsEnabled] = useState(true);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [nodes, setNodes] = useState<Node[]>([
    {
      id: "trigger-1",
      type: "trigger",
      category: "time",
      title: "Every Day at 9:00 AM",
      icon: Clock,
      config: "Daily schedule",
    },
  ]);

  const triggers = [
    { category: "time", title: "Time-based Trigger", icon: Clock },
    { category: "webhook", title: "Webhook Trigger", icon: Webhook },
    { category: "calendar", title: "Google Calendar Event", icon: Calendar },
  ];

  const actions = [
    { category: "email", title: "Send Email", icon: Mail },
    { category: "notification", title: "Send Notification", icon: Bell },
    { category: "api", title: "API Call", icon: Code },
    { category: "ai", title: "AI Suggestion", icon: Sparkles },
  ];

  const addTrigger = (trigger: any) => {
    const newNode: Node = {
      id: `trigger-${Date.now()}`,
      type: "trigger",
      category: trigger.category,
      title: trigger.title,
      icon: trigger.icon,
      config: "Not configured",
    };
    const existingTriggerIndex = nodes.findIndex((node) => node.type === "trigger");
    if (existingTriggerIndex !== -1) {
      const updatedNodes = [...nodes];
      updatedNodes[existingTriggerIndex] = newNode;
      setNodes(updatedNodes);
    } else {
      setNodes([newNode, ...nodes]);
    }
    setSelectedNode(newNode);
  };

  const addAction = (action: any) => {
    const newNode: Node = {
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
    const updatedNodes = nodes.filter((node) => node.id !== nodeId);
    setNodes(updatedNodes);
    if (selectedNode?.id === nodeId) {
      setSelectedNode(null);
    }
  };

  const updateNodeProperty = (nodeId: string, property: keyof Node, value: any) => {
    const updatedNodes = nodes.map((node) =>
      node.id === nodeId ? { ...node, [property]: value } : node
    );
    setNodes(updatedNodes);
    if (selectedNode?.id === nodeId) {
      setSelectedNode({ ...selectedNode, [property]: value });
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <div className="w-64 border-r border-gray-200 bg-gray-50 p-4 overflow-y-auto">
        <div className="mb-6">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-600">
            Triggers
          </h3>
          <div className="space-y-2">
            {triggers.map((trigger, index) => {
              const Icon = trigger.icon;
              return (
                <div
                  key={index}
                  onClick={() => addTrigger(trigger)}
                  className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:border-blue-300 transition-colors"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-blue-50">
                    <Icon className="h-4 w-4 text-blue-600" />
                  </div>
                  <span className="text-sm font-medium text-gray-900">{trigger.title}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-600">
            Actions
          </h3>
          <div className="space-y-2">
            {actions.map((action, index) => {
              const Icon = action.icon;
              return (
                <div
                  key={index}
                  onClick={() => addAction(action)}
                  className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:border-blue-300 transition-colors"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-gray-100">
                    <Icon className="h-4 w-4 text-gray-700" />
                  </div>
                  <span className="text-sm font-medium text-gray-900">{action.title}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="flex-1 bg-gray-50 overflow-y-auto">
        <div className="border-b border-gray-200 bg-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                className="border-0 bg-transparent text-xl font-semibold text-gray-900 focus:outline-none focus:ring-0"
              />
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={(e) => setIsEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">Enabled</span>
              </label>
            </div>
            <div className="flex items-center gap-3">
              <button className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                <Play className="inline h-4 w-4 mr-2" />
                Run Test
              </button>
              <button
                onClick={() => navigate("/dashboard/workflows")}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                <Save className="inline h-4 w-4 mr-2" />
                Save
              </button>
            </div>
          </div>
        </div>

        <div className="flex items-start justify-center p-8">
          <div className="w-full max-w-2xl space-y-4">
            {nodes.map((node, index) => {
              const Icon = node.icon;
              return (
                <div key={node.id}>
                  <div
                    onClick={() => setSelectedNode(node)}
                    className={`cursor-pointer rounded-lg border-2 bg-white p-4 shadow-sm transition-all ${
                      selectedNode?.id === node.id
                        ? "border-blue-500 ring-2 ring-blue-200"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <GripVertical className="h-5 w-5 text-gray-400" />
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                        <Icon className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{node.title}</div>
                        <div className="text-sm text-gray-500">{node.config}</div>
                      </div>
                      <div
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          node.type === "trigger"
                            ? "bg-purple-50 text-purple-700"
                            : "bg-blue-50 text-blue-700"
                        }`}
                      >
                        {node.type === "trigger" ? "Trigger" : "Action"}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeNode(node.id);
                        }}
                        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        aria-label="Remove node"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  {index < nodes.length - 1 && (
                    <div className="flex justify-center py-2">
                      <div className="h-8 w-0.5 bg-gray-300"></div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {selectedNode && (
        <div className="w-80 border-l border-gray-200 bg-white p-6 overflow-y-auto">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Properties</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              aria-label="Close properties"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Node Type</label>
              <input
                type="text"
                value={selectedNode.type === "trigger" ? "Trigger" : "Action"}
                disabled
                className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={selectedNode.title}
                onChange={(e) => updateNodeProperty(selectedNode.id, "title", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Details
              </label>
              <textarea
                rows={4}
                value={selectedNode.config || ""}
                onChange={(e) => updateNodeProperty(selectedNode.id, "config", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Enter additional details or notes..."
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
