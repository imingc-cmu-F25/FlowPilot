import { useEffect, useRef, useState } from "react";
import { Sparkles, X, Send, Wand2 } from "lucide-react";
import type {
  PendingQuestion,
  SuggestionAnalysis,
  WorkflowDefinition,
} from "../../lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  workflowDraft?: WorkflowDefinition | null;
  suggestionId?: string;
  analysis?: SuggestionAnalysis | null;
  pendingQuestions?: PendingQuestion[];
}

interface AIChatPanelProps {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onClose: () => void;
  onApplyDraft?: (draft: WorkflowDefinition, suggestionId?: string) => void;
  onAnswer?: (
    suggestionId: string,
    answers: Record<string, string>,
  ) => Promise<void> | void;
  loading?: boolean;
}

function PendingQuestionsForm({
  suggestionId,
  questions,
  onSubmit,
}: {
  suggestionId: string;
  questions: PendingQuestion[];
  onSubmit: (answers: Record<string, string>) => Promise<void> | void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((q) => [q.field, q.suggested_value || ""])),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    e.preventDefault();
    // Require every field to be non-empty before submitting.
    const missing = questions.filter((q) => !values[q.field]?.trim());
    if (missing.length > 0) {
      setError(`Please answer: ${missing.map((q) => q.field).join(", ")}`);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Failed to submit answers.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      data-suggestion-id={suggestionId}
      className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-3"
    >
      <p className="text-xs font-semibold text-amber-900">
        I need a bit more info before I can finalize the workflow:
      </p>
      {questions.map((q) => (
        <div key={q.field} className="space-y-1">
          <label className="block text-xs text-amber-900">
            {q.question}
          </label>
          <input
            type="text"
            value={values[q.field] ?? ""}
            placeholder={q.example || ""}
            onChange={(ev) =>
              setValues((prev) => ({ ...prev, [q.field]: ev.target.value }))
            }
            disabled={submitting}
            className="w-full rounded-md border border-amber-300 bg-white px-2 py-1 text-xs focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          {q.example && (
            <p className="text-[10px] text-amber-700/80">e.g. {q.example}</p>
          )}
        </div>
      ))}
      {error && (
        <p className="text-xs text-red-700">{error}</p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="inline-flex items-center gap-1 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-amber-700 disabled:bg-amber-300"
      >
        {submitting ? "Submitting…" : "Continue"}
      </button>
    </form>
  );
}

export function AIChatPanel({
  messages,
  input,
  onInputChange,
  onSend,
  onClose,
  onApplyDraft,
  onAnswer,
  loading = false,
}: AIChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Keep the latest message / "Thinking…" indicator in view. Scroll the
  // inner messages container rather than the window so the surrounding
  // builder page doesn't jump.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex h-full w-full flex-col border-l border-gray-200 bg-white sm:w-80 md:w-96">
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

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
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
              {message.role === "assistant" && message.analysis && (
                <div className="flex flex-wrap gap-1 text-[10px] text-gray-500">
                  <span className="rounded-full bg-gray-100 px-2 py-0.5">
                    {message.analysis.complexity_level}
                  </span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5">
                    {message.analysis.input_type}
                  </span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5">
                    confidence {Math.round(message.analysis.confidence * 100)}%
                  </span>
                </div>
              )}
              {message.role === "assistant" &&
                message.suggestionId &&
                message.pendingQuestions &&
                message.pendingQuestions.length > 0 && (
                  <PendingQuestionsForm
                    suggestionId={message.suggestionId}
                    questions={message.pendingQuestions}
                    onSubmit={(answers) =>
                      onAnswer?.(message.suggestionId!, answers) ??
                      Promise.resolve()
                    }
                  />
                )}
              {message.role === "assistant" &&
                message.workflowDraft &&
                (!message.pendingQuestions ||
                  message.pendingQuestions.length === 0) && (
                  <div className="rounded-lg border border-purple-200 bg-purple-50 p-3">
                    <p className="mb-2 text-xs font-semibold text-purple-900">
                      Suggested workflow: {message.workflowDraft.name}
                    </p>
                    <p className="mb-2 text-xs text-purple-700">
                      Trigger: {message.workflowDraft.trigger?.type} •{" "}
                      {message.workflowDraft.steps?.length ?? 0} step(s)
                    </p>
                    <button
                      onClick={() =>
                        onApplyDraft?.(
                          message.workflowDraft!,
                          message.suggestionId,
                        )
                      }
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
