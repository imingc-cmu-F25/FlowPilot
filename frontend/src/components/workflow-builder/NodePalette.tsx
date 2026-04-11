import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface PaletteItem {
  category: string;
  title: string;
  icon: React.ElementType;
}

interface NodePaletteProps {
  triggers: PaletteItem[];
  actions: PaletteItem[];
  onAddTrigger: (trigger: PaletteItem) => void;
  onAddAction: (action: PaletteItem) => void;
}

function PaletteItemRow({
  item,
  variant,
  onClick,
  collapsed,
}: {
  item: PaletteItem;
  variant: "trigger" | "action";
  onClick: () => void;
  collapsed: boolean;
}) {
  const Icon = item.icon;
  return (
    <div
      onClick={onClick}
      title={collapsed ? item.title : undefined}
      className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-colors hover:border-blue-300"
    >
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded ${
          variant === "trigger" ? "bg-blue-50" : "bg-gray-100"
        }`}
      >
        <Icon
          className={`h-4 w-4 ${variant === "trigger" ? "text-blue-600" : "text-gray-700"}`}
        />
      </div>
      {!collapsed && (
        <span className="text-sm font-medium text-gray-900">{item.title}</span>
      )}
    </div>
  );
}

export function NodePalette({ triggers, actions, onAddTrigger, onAddAction }: NodePaletteProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={`relative flex shrink-0 flex-col overflow-y-auto border-r border-gray-200 bg-gray-50 transition-all duration-200 ${
        collapsed ? "w-14" : "w-48 sm:w-56 md:w-64"
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute right-1 top-2 z-10 rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
        aria-label={collapsed ? "Expand palette" : "Collapse palette"}
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      <div className={`p-2 pt-8 sm:p-4 sm:pt-8 ${collapsed ? "px-1.5" : ""}`}>
        <div className="mb-4 sm:mb-6">
          {!collapsed && (
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-600 sm:mb-3">
              Triggers
            </h3>
          )}
          <div className="space-y-2">
            {triggers.map((trigger, index) => (
              <PaletteItemRow
                key={index}
                item={trigger}
                variant="trigger"
                collapsed={collapsed}
                onClick={() => onAddTrigger(trigger)}
              />
            ))}
          </div>
        </div>

        <div>
          {!collapsed && (
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-600 sm:mb-3">
              Actions
            </h3>
          )}
          <div className="space-y-2">
            {actions.map((action, index) => (
              <PaletteItemRow
                key={index}
                item={action}
                variant="action"
                collapsed={collapsed}
                onClick={() => onAddAction(action)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
