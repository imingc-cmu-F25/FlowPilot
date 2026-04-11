interface IconCardProps {
  icon: React.ElementType;
  label: string;
  iconClassName?: string;
}

export function IconCard({ icon: Icon, label, iconClassName = "h-6 w-6 text-blue-600" }: IconCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-lg">
      <div className="flex items-center gap-3">
        <Icon className={iconClassName} />
        <span className="text-sm font-medium">{label}</span>
      </div>
    </div>
  );
}
