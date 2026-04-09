import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { HomeTopBar } from "../components/HomeTopBar";
import { getStoredUsername } from "../auth/storage";
import {
  appendUserEmail,
  deleteUserEmail,
  editUserEmail,
  fetchAllUsers,
  type EmailAddress,
} from "../lib/api";

export function ProfilePage() {
  const username = getStoredUsername();
  const [emails, setEmails] = useState<EmailAddress[]>([]);
  const [newAddress, setNewAddress] = useState("");
  const [newAlias, setNewAlias] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingAddress, setEditingAddress] = useState<string | null>(null);
  const [editAddress, setEditAddress] = useState("");
  const [editAlias, setEditAlias] = useState("");
  const [actionPending, setActionPending] = useState<string | null>(null);

  const loadEmails = useCallback(async () => {
    if (!username) return;
    setLoading(true);
    setError(null);
    try {
      const users = await fetchAllUsers();
      const me = users.find((u) => u.name === username);
      setEmails(me?.emails ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load emails");
      setEmails([]);
    } finally {
      setLoading(false);
    }
  }, [username]);

  useEffect(() => {
    void loadEmails();
  }, [loadEmails]);

  const handleDeleteEmail = async (address: string) => {
    if (!username) return;
    setActionPending(address);
    setError(null);
    try {
      const updated = await deleteUserEmail(username, address);
      setEmails(updated.emails);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete email");
    } finally {
      setActionPending(null);
    }
  };

  const startEdit = (row: EmailAddress) => {
    setEditingAddress(row.address);
    setEditAddress(row.address);
    setEditAlias(row.alias);
    setError(null);
  };

  const cancelEdit = () => {
    setEditingAddress(null);
    setEditAddress("");
    setEditAlias("");
  };

  const handleEditEmail = async (e: FormEvent, oldAddress: string) => {
    e.preventDefault();
    if (!username) return;
    const newAddress = editAddress.trim();
    if (!newAddress) {
      setError("Email address is required");
      return;
    }
    setActionPending(oldAddress);
    setError(null);
    try {
      const updated = await editUserEmail(username, oldAddress, newAddress, editAlias.trim());
      setEmails(updated.emails);
      cancelEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update email");
    } finally {
      setActionPending(null);
    }
  };

  const handleAddEmail = async (e: FormEvent) => {
    e.preventDefault();
    if (!username?.trim()) return;
    const address = newAddress.trim();
    const alias = newAlias.trim();
    if (!address) {
      setError("Email address is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await appendUserEmail(username, address, alias);
      setEmails(updated.emails);
      setNewAddress("");
      setNewAlias("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add email");
    } finally {
      setSaving(false);
    }
  };

  if (!username) {
    return (
      <div className="min-h-screen bg-white">
        <HomeTopBar />
        <div className="mx-auto max-w-7xl px-6 py-8">
          <p className="text-gray-700">
            Sign in to manage your profile and email addresses.{" "}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <HomeTopBar />
      <div className="mx-auto max-w-7xl px-6 py-8">
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">Profile</h1>
        <div className="space-y-8">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Account</h2>
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Username</label>
              <p className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-gray-900">
                {username}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">Email addresses</h2>
            {error && (
              <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
                {error}
              </p>
            )}
            {loading ? (
              <p className="text-sm text-gray-600">Loading…</p>
            ) : emails.length === 0 ? (
              <p className="text-sm text-gray-600">No email addresses yet.</p>
            ) : (
              <ul className="mb-6 space-y-2">
                {emails.map((row) => (
                  <li
                    key={`${row.address}-${row.alias}`}
                    className="rounded-lg border border-gray-200 px-4 py-3"
                  >
                    {editingAddress === row.address ? (
                      <form onSubmit={(e) => handleEditEmail(e, row.address)} className="space-y-3">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">Email address</label>
                          <input
                            type="email"
                            value={editAddress}
                            onChange={(e) => setEditAddress(e.target.value)}
                            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">Alias</label>
                          <input
                            type="text"
                            value={editAlias}
                            onChange={(e) => setEditAlias(e.target.value)}
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
                            onClick={cancelEdit}
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
                          {row.alias ? (
                            <span className="text-sm text-gray-500">{row.alias}</span>
                          ) : null}
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(row)}
                            disabled={actionPending !== null}
                            className="rounded-lg border border-gray-300 px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteEmail(row.address)}
                            disabled={actionPending === row.address}
                            className="rounded-lg border border-red-200 px-3 py-1 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            {actionPending === row.address ? "Deleting…" : "Delete"}
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}

            <h3 className="mb-3 text-sm font-semibold text-gray-900">Add email</h3>
            <form onSubmit={handleAddEmail} className="space-y-4">
              <div>
                <label htmlFor="new-email" className="mb-1 block text-sm font-medium text-gray-700">
                  Email address
                </label>
                <input
                  id="new-email"
                  type="email"
                  value={newAddress}
                  onChange={(e) => setNewAddress(e.target.value)}
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
                  value={newAlias}
                  onChange={(e) => setNewAlias(e.target.value)}
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
          </div>
        </div>
      </div>
    </div>
  );
}
