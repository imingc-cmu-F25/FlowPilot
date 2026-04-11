import { Search } from "lucide-react";

type FilterValue = "all" | "active" | "disabled";

interface WorkflowSearchBarProps {
  search: string;
  filter: FilterValue;
  onSearchChange: (value: string) => void;
  onFilterChange: (value: FilterValue) => void;
}

export function WorkflowSearchBar({
  search,
  filter,
  onSearchChange,
  onFilterChange,
}: WorkflowSearchBarProps) {
  return (
    <div className="mb-6 flex items-center gap-4">
      <div className="relative max-w-md flex-1">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search workflows..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <select
        value={filter}
        onChange={(e) => onFilterChange(e.target.value as FilterValue)}
        className="rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="all">All Workflows</option>
        <option value="active">Active</option>
        <option value="disabled">Disabled</option>
      </select>
    </div>
  );
}
