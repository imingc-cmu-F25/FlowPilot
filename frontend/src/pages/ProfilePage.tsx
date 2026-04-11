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
import { AccountCard } from "../components/profile/AccountCard";
import { EmailListItem } from "../components/profile/EmailListItem";
import { AddEmailForm } from "../components/profile/AddEmailForm";

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
    const newAddr = editAddress.trim();
    if (!newAddr) {
      setError("Email address is required");
      return;
    }
    setActionPending(oldAddress);
    setError(null);
    try {
      const updated = await editUserEmail(username, oldAddress, newAddr, editAlias.trim());
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
          <AccountCard username={username} />

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
                  <EmailListItem
                    key={`${row.address}-${row.alias}`}
                    row={row}
                    isEditing={editingAddress === row.address}
                    editAddress={editAddress}
                    editAlias={editAlias}
                    actionPending={actionPending}
                    onStartEdit={() => startEdit(row)}
                    onCancelEdit={cancelEdit}
                    onChangeEditAddress={setEditAddress}
                    onChangeEditAlias={setEditAlias}
                    onSubmitEdit={(e) => handleEditEmail(e, row.address)}
                    onDelete={() => handleDeleteEmail(row.address)}
                  />
                ))}
              </ul>
            )}

            <AddEmailForm
              address={newAddress}
              alias={newAlias}
              saving={saving}
              onChangeAddress={setNewAddress}
              onChangeAlias={setNewAlias}
              onSubmit={handleAddEmail}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
