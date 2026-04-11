import type { FormEvent } from "react";
import type { EmailAddress } from "../../lib/api";

interface EmailListItemProps {
  row: EmailAddress;
  isEditing: boolean;
  editAddress: string;
  editAlias: string;
  actionPending: string | null;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onChangeEditAddress: (value: string) => void;
  onChangeEditAlias: (value: string) => void;
  onSubmitEdit: (e: FormEvent) => void;
  onDelete: () => void;
}

export function EmailListItem({
  row,
  isEditing,
  editAddress,
  editAlias,
  actionPending,
  onStartEdit,
  onCancelEdit,
  onChangeEditAddress,
  onChangeEditAlias,
  onSubmitEdit,
  onDelete,
}: EmailListItemProps) {
  return (
    <li className="rounded-lg border border-gray-200 px-4 py-3">
      {isEditing ? (
        <form onSubmit={onSubmitEdit} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Email address</label>
            <input
              type="email"
              value={editAddress}
              onChange={(e) => onChangeEditAddress(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Alias</label>
            <input
              type="text"
              value={editAlias}
              onChange={(e) => onChangeEditAlias(e.target.value)}
              placeholder="Work, school, personal…"
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={actionPending === row.address}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {actionPending === row.address ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={onCancelEdit}
              className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="font-medium text-gray-900">{row.address}</span>
            {row.alias ? <span className="text-sm text-gray-500">{row.alias}</span> : null}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onStartEdit}
              disabled={actionPending !== null}
              className="rounded-lg border border-gray-300 px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={onDelete}
              disabled={actionPending === row.address}
              className="rounded-lg border border-red-200 px-3 py-1 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {actionPending === row.address ? "Deleting…" : "Delete"}
            </button>
          </div>
        </div>
      )}
    </li>
  );
}
