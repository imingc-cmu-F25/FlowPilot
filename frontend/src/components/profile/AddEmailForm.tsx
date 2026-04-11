import type { FormEvent } from "react";

interface AddEmailFormProps {
  address: string;
  alias: string;
  saving: boolean;
  onChangeAddress: (value: string) => void;
  onChangeAlias: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
}

export function AddEmailForm({
  address,
  alias,
  saving,
  onChangeAddress,
  onChangeAlias,
  onSubmit,
}: AddEmailFormProps) {
  return (
    <>
      <h3 className="mb-3 text-sm font-semibold text-gray-900">Add email</h3>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label htmlFor="new-email" className="mb-1 block text-sm font-medium text-gray-700">
            Email address
          </label>
          <input
            id="new-email"
            type="email"
            value={address}
            onChange={(e) => onChangeAddress(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label htmlFor="new-alias" className="mb-1 block text-sm font-medium text-gray-700">
            Alias
          </label>
          <input
            id="new-alias"
            type="text"
            value={alias}
            onChange={(e) => onChangeAlias(e.target.value)}
            placeholder="Work, school, personal…"
            className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Adding…" : "Add email"}
        </button>
      </form>
    </>
  );
}
