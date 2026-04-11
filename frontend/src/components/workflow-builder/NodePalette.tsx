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
}: {
  item: PaletteItem;
  variant: "trigger" | "action";
  onClick: () => void;
}) {
  const Icon = item.icon;
  return (
    <div
      onClick={onClick}
      className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-colors hover:border-blue-300"
    >
      <div
        className={`flex h-8 w-8 items-center justify-center rounded ${
          variant === "trigger" ? "bg-blue-50" : "bg-gray-100"
        }`}
      >
        <Icon
          className={`h-4 w-4 ${variant === "trigger" ? "text-blue-600" : "text-gray-700"}`}
        />
      </div>
      <span className="text-sm font-medium text-gray-900">{item.title}</span>
    </div>
  );
}

export function NodePalette({ triggers, actions, onAddTrigger, onAddAction }: NodePaletteProps) {
  return (
    <div className="w-64 overflow-y-auto border-r border-gray-200 bg-gray-50 p-4">
      <div className="mb-6">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-600">
          Triggers
        </h3>
        <div className="space-y-2">
          {triggers.map((trigger, index) => (
            <PaletteItemRow
              key={index}
              item={trigger}
              variant="trigger"
              onClick={() => onAddTrigger(trigger)}
            />
          ))}
        </div>
      </div>
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-600">
          Actions
        </h3>
        <div className="space-y-2">
          {actions.map((action, index) => (
            <PaletteItemRow
              key={index}
              item={action}
              variant="action"
              onClick={() => onAddAction(action)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
