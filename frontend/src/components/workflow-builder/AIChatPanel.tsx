import { Sparkles, X, Send, Wand2 } from "lucide-react";
import type { WorkflowDefinition } from "../../lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  workflowDraft?: WorkflowDefinition | null;
  suggestionId?: string;
}

interface AIChatPanelProps {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onClose: () => void;
  onApplyDraft?: (draft: WorkflowDefinition) => void;
  loading?: boolean;
}

export function AIChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  onClose,
  onApplyDraft,
  loading = false,
}: AIChatPanelProps) {
  return (
    <div className="flex w-full flex-col border-l border-gray-200 bg-white sm:w-80 md:w-96">
      <div className="flex items-center justify-between border-b border-gray-200 p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100">
            <Sparkles className="h-4 w-4 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">AI Assistant</h3>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close AI chat"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] ${
                message.role === "user" ? "" : "space-y-2"
              }`}
            >
              <div
                className={`rounded-lg px-4 py-2 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              </div>
              {message.role === "assistant" && message.workflowDraft && (
                <div className="rounded-lg border border-purple-200 bg-purple-50 p-3">
                  <p className="mb-2 text-xs font-semibold text-purple-900">
                    Suggested workflow: {message.workflowDraft.name}
                  </p>
                  <p className="mb-2 text-xs text-purple-700">
                    Trigger: {message.workflowDraft.trigger?.type} •{" "}
                    {message.workflowDraft.steps?.length ?? 0} step(s)
                  </p>
                  <button
                    onClick={() => onApplyDraft?.(message.workflowDraft!)}
                    className="inline-flex items-center gap-1 rounded-md bg-purple-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-purple-700"
                  >
                    <Wand2 className="h-3 w-3" />
                    Apply to Canvas
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-100 px-4 py-2 text-sm text-gray-500">
              Thinking…
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-gray-200 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && onSend()}
            placeholder="Ask me anything..."
            disabled={loading}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:bg-gray-50"
          />
          <button
            onClick={onSend}
            disabled={loading}
            className="rounded-lg bg-purple-600 p-2 text-white transition-colors hover:bg-purple-700 disabled:bg-purple-300"
            aria-label="Send message"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
