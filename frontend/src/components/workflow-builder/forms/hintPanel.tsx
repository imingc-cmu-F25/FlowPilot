import type { ReactNode } from "react";

// Shared visual language for the "available template variables" reference
// cards that live at the bottom of each action form. The forms used to
// roll their own boxes in slightly different shades of blue / gray; this
// module centralises the look so Create Calendar Event, Send Email and
// List Upcoming Events feel like the same product.
//
// Design intent:
// - collapsed by default so the form stays compact
// - neutral palette (no chromatic "alert" look)
// - tight typography (11px body / 10px uppercase labels) so dense
//   reference material doesn't dominate the form

interface HintPanelProps {
  summary: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function HintPanel({ summary, defaultOpen, children }: HintPanelProps) {
  return (
    <details
      className="group rounded-xl border border-gray-200 bg-white"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer select-none items-center justify-between px-4 py-3 text-sm font-medium text-gray-900">
        <span>{summary}</span>
        {/* Heroicons "chevron-down" — rotates 180° when open */}
        <svg
          className="h-4 w-4 text-gray-400 transition-transform group-open:rotate-180"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 011.08 1.04l-4.24 4.5a.75.75 0 01-1.08 0l-4.24-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </summary>
      <div className="space-y-4 border-t border-gray-100 px-4 py-3">
        {children}
      </div>
    </details>
  );
}

interface HintSectionProps {
  label: string;
  children: ReactNode;
}

export function HintSection({ label, children }: HintSectionProps) {
  return (
    <section>
      <h5 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
        {label}
      </h5>
      {children}
    </section>
  );
}

interface HintItemProps {
  /** One or more code snippets shown as chips on the same line. */
  codes: string[];
  /** Optional muted suffix after the chips (e.g. "(End field only)"). */
  note?: string;
  /** The human-readable description below the chips. */
  children: ReactNode;
}

export function HintItem({ codes, note, children }: HintItemProps) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-1">
        {codes.map((code) => (
          <Chip key={code}>{code}</Chip>
        ))}
        {note ? (
          <span className="text-[11px] text-gray-400">{note}</span>
        ) : null}
      </div>
      <p className="text-[11px] leading-relaxed text-gray-600">{children}</p>
    </div>
  );
}

interface ChipProps {
  children: ReactNode;
}

export function Chip({ children }: ChipProps) {
  return (
    <code className="inline-flex max-w-full break-all rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 font-mono text-[11px] text-gray-700">
      {children}
    </code>
  );
}

/** Intro paragraph inside a HintPanel — keeps typography consistent. */
export function HintIntro({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] leading-relaxed text-gray-600">{children}</p>
  );
}

/** Smaller muted footnote (used for Google-OAuth fallback note etc.). */
export function HintFootnote({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] leading-relaxed text-gray-400">{children}</p>
  );
}

export function HintDL({ children }: { children: ReactNode }) {
  return <dl className="space-y-3">{children}</dl>;
}
