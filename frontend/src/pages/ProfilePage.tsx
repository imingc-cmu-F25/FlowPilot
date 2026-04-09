import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { HomeTopBar } from "../components/HomeTopBar";
import { getStoredUsername } from "../auth/storage";
import {
  appendUserEmail,
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
                    className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-gray-200 px-4 py-3"
                  >
                    <span className="font-medium text-gray-900">{row.address}</span>
                    {row.alias ? (
                      <span className="text-sm text-gray-500">{row.alias}</span>
                    ) : null}
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
