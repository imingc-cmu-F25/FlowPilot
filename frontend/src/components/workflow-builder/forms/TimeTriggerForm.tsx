import { useEffect } from "react";
import { browserTimezone, type TimeTriggerConfig } from "../nodeConfig";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface Props {
  config: TimeTriggerConfig;
  onChange: (config: TimeTriggerConfig) => void;
}

export function TimeTriggerForm({ config, onChange }: Props) {
  const rec = config.recurrence;
  const detectedTz = browserTimezone();
  const storedTzMismatch =
    config.timezone && config.timezone !== detectedTz && config.timezone !== "UTC";

  // Keep the stored timezone in sync with the browser's zone. The datetime
  // picker's value is always interpreted as browser-local when we convert to
  // UTC on save, so persisting anything else here would be a lie and would
  // confuse users who later edit the workflow on a different machine.
  useEffect(() => {
    if (config.timezone !== detectedTz) {
      onChange({ ...config, timezone: detectedTz });
    }
    // We intentionally run this once per detected zone change; listing the
    // full config in the dep array would cause a loop with onChange.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detectedTz]);

  function set<K extends keyof TimeTriggerConfig>(key: K, value: TimeTriggerConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  function setRec<K extends keyof NonNullable<TimeTriggerConfig["recurrence"]>>(
    key: K,
    value: NonNullable<TimeTriggerConfig["recurrence"]>[K],
  ) {
    if (!rec) return;
    onChange({ ...config, recurrence: { ...rec, [key]: value } });
  }

  function toggleRecurrence(enabled: boolean) {
    onChange({
      ...config,
      recurrence: enabled
        ? { frequency: "daily", interval: 1, days_of_week: [], cron_expression: "" }
        : null,
    });
  }

  function toggleDay(day: number) {
    if (!rec) return;
    const days = rec.days_of_week.includes(day)
      ? rec.days_of_week.filter((d) => d !== day)
      : [...rec.days_of_week, day].sort();
    setRec("days_of_week", days);
  }

  return (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
        <input
          type="text"
          value={config.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="E.g. Every morning at 9 AM"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Trigger datetime */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Trigger date &amp; time
        </label>
        <input
          type="datetime-local"
          value={config.trigger_at}
          onChange={(e) => set("trigger_at", e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Interpreted in your timezone:{" "}
          <span className="font-mono text-gray-700">{detectedTz}</span>
        </p>
        {storedTzMismatch && (
          <p className="mt-1 text-xs text-amber-600">
            This workflow was originally saved with timezone{" "}
            <span className="font-mono">{config.timezone}</span>. Saving now
            will re-stamp it with your current browser zone above.
          </p>
        )}
      </div>

      {/* Recurrence toggle */}
      <div className="flex items-center gap-2">
        <input
          id="recurrence-toggle"
          type="checkbox"
          checked={rec !== null}
          onChange={(e) => toggleRecurrence(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="recurrence-toggle" className="text-sm font-medium text-gray-700">
          Repeat on a schedule
        </label>
      </div>

      {/* Recurrence fields */}
      {rec && (
        <div className="space-y-3 rounded-lg border border-blue-100 bg-blue-50 p-3">
          {/* Frequency */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Frequency</label>
            <select
              value={rec.frequency}
              onChange={(e) =>
                setRec(
                  "frequency",
                  e.target.value as NonNullable<TimeTriggerConfig["recurrence"]>["frequency"],
                )
              }
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="minutely">Minutely</option>
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="custom">Custom (cron)</option>
            </select>
          </div>

          {/* Interval — not shown for custom */}
          {rec.frequency !== "custom" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Repeat every
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  value={rec.interval}
                  onChange={(e) => setRec("interval", Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">
                  {rec.frequency === "minutely" && (rec.interval === 1 ? "minute" : "minutes")}
                  {rec.frequency === "hourly" && (rec.interval === 1 ? "hour" : "hours")}
                  {rec.frequency === "daily" && (rec.interval === 1 ? "day" : "days")}
                  {rec.frequency === "weekly" && (rec.interval === 1 ? "week" : "weeks")}
                </span>
              </div>
            </div>
          )}

          {/* Days of week — weekly only */}
          {rec.frequency === "weekly" && (
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">On days</label>
              <div className="flex gap-1">
                {DAYS.map((label, idx) => {
                  const active = rec.days_of_week.includes(idx);
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleDay(idx)}
                      className={`flex h-8 w-9 items-center justify-center rounded text-xs font-medium transition-colors ${
                        active
                          ? "bg-blue-600 text-white"
                          : "border border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Cron expression — custom only */}
          {rec.frequency === "custom" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Cron expression
              </label>
              <input
                type="text"
                value={rec.cron_expression}
                onChange={(e) => setRec("cron_expression", e.target.value)}
                placeholder="0 9 * * 1-5"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                minute hour day-of-month month day-of-week
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
