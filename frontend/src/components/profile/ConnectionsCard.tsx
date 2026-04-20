import { useCallback, useEffect, useState } from "react";
import {
  beginGoogleAuthorize,
  disconnectGoogle,
  fetchGoogleEvents,
  fetchGoogleStatus,
  syncGoogleCalendar,
  type CachedCalendarEvent,
  type GoogleCalendarStatus,
} from "../../lib/api";

type BannerKind = "success" | "error" | null;

export function ConnectionsCard() {
  const [status, setStatus] = useState<GoogleCalendarStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"connect" | "sync" | "disconnect" | null>(
    null,
  );
  const [banner, setBanner] = useState<{ kind: BannerKind; text: string }>({
    kind: null,
    text: "",
  });
  const [events, setEvents] = useState<CachedCalendarEvent[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s = await fetchGoogleStatus();
      setStatus(s);
      if (s.connected) {
        try {
          const ev = await fetchGoogleEvents(10);
          setEvents(ev);
        } catch {
          setEvents([]);
        }
      } else {
        setEvents([]);
      }
    } catch (e) {
      setBanner({
        kind: "error",
        text: e instanceof Error ? e.message : "Failed to load status",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // React to the OAuth redirect back to /dashboard/integrations?google_calendar=...
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const flag = params.get("google_calendar");
    if (!flag) return;
    if (flag === "connected") {
      setBanner({
        kind: "success",
        text: "Google Calendar connected.",
      });
    } else if (flag === "error") {
      const reason = params.get("reason") ?? "unknown";
      setBanner({
        kind: "error",
        text: `Google Calendar authorization failed (${reason}).`,
      });
    }
    params.delete("google_calendar");
    params.delete("reason");
    params.delete("detail");
    const next = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${next ? `?${next}` : ""}`,
    );
    void load();
  }, [load]);

  const handleConnect = async () => {
    setBusy("connect");
    setBanner({ kind: null, text: "" });
    try {
      const { authorize_url } = await beginGoogleAuthorize();
      window.location.href = authorize_url;
    } catch (e) {
      setBanner({
        kind: "error",
        text: e instanceof Error ? e.message : "Unable to start authorization",
      });
      setBusy(null);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm("Disconnect Google Calendar? Cached events will be cleared.")) return;
    setBusy("disconnect");
    setBanner({ kind: null, text: "" });
    try {
      await disconnectGoogle();
      setBanner({ kind: "success", text: "Google Calendar disconnected." });
      await load();
    } catch (e) {
      setBanner({
        kind: "error",
        text: e instanceof Error ? e.message : "Failed to disconnect",
      });
    } finally {
      setBusy(null);
    }
  };

  const handleSync = async () => {
    setBusy("sync");
    setBanner({ kind: null, text: "" });
    try {
      const result = await syncGoogleCalendar("primary");
      setBanner({
        kind: "success",
        text: `Synced ${result.synced} event${result.synced === 1 ? "" : "s"}.`,
      });
      await load();
    } catch (e) {
      setBanner({
        kind: "error",
        text: e instanceof Error ? e.message : "Sync failed",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      {banner.kind && (
        <p
          className={`mb-4 rounded-lg border px-4 py-2 text-sm ${
            banner.kind === "success"
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}
        >
          {banner.text}
        </p>
      )}

      <div className="flex flex-col gap-3 border-b border-gray-100 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-base font-medium text-gray-900">
              Google Calendar
            </p>
            <p className="text-sm text-gray-600">
              {loading
                ? "Loading…"
                : !status?.configured
                  ? "Server is missing GOOGLE_CLIENT_ID / SECRET; actions will fall back to mock events."
                  : status?.connected
                    ? "Connected — workflows will create real calendar events."
                    : "Not connected — CalendarCreateEvent actions return mock events."}
            </p>
          </div>
          <div className="flex gap-2">
            {status?.connected ? (
              <>
                <button
                  type="button"
                  onClick={handleSync}
                  disabled={busy !== null}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy === "sync" ? "Syncing…" : "Sync now"}
                </button>
                <button
                  type="button"
                  onClick={handleDisconnect}
                  disabled={busy !== null}
                  className="rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy === "disconnect" ? "Disconnecting…" : "Disconnect"}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleConnect}
                disabled={busy !== null || !status?.configured}
                className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy === "connect" ? "Redirecting…" : "Connect Google Calendar"}
              </button>
            )}
          </div>
        </div>

        {status?.connected && (
          <div className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600">
            <p>Scopes: {status.connection?.scopes.join(", ") || "—"}</p>
            {status.connection?.expiry && (
              <p>
                Access token expires:{" "}
                {new Date(status.connection.expiry).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>

      {status?.connected && (
        <div className="mt-4">
          <h3 className="mb-2 text-sm font-semibold text-gray-900">
            Cached upcoming events
          </h3>
          {events.length === 0 ? (
            <p className="text-sm text-gray-600">
              No cached events yet. Click "Sync now" to pull the next 30 days.
            </p>
          ) : (
            <ul className="space-y-2">
              {events.map((ev) => (
                <li
                  key={ev.id}
                  className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
                >
                  <div className="font-medium text-gray-900">{ev.title}</div>
                  <div className="text-xs text-gray-600">
                    {ev.start ? new Date(ev.start).toLocaleString() : "No start"}
                    {" — "}
                    {ev.end ? new Date(ev.end).toLocaleString() : "No end"}
                  </div>
                  {ev.html_link && (
                    <a
                      href={ev.html_link}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Open in Google Calendar ↗
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
