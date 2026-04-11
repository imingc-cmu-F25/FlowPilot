from datetime import datetime
from enum import StrEnum

from croniter import croniter
from pydantic import BaseModel


class RecurrenceFrequency(StrEnum):
    MINUTELY = "minutely"
    HOURLY   = "hourly"
    DAILY    = "daily"
    WEEKLY   = "weekly"
    CUSTOM   = "custom"


class RecurrenceRule(BaseModel):
    """
    Defines a repeating schedule anchored to TimeTriggerConfig.trigger_at.

    E.g.:
        Every 2 days:
            RecurrenceRule(frequency="daily", interval=2)

        Every Monday and Friday:
            RecurrenceRule(frequency="weekly", days_of_week=[0, 4])

        Every other week on Wednesday:
            RecurrenceRule(frequency="weekly", interval=2, days_of_week=[2])

        9 AM on weekdays (custom cron):
            RecurrenceRule(frequency="custom", cron_expression="0 9 * * 1-5")
    """
    frequency: RecurrenceFrequency
    interval: int = 1 
    days_of_week: list[int] = []    # 0=Mon ... 6=Sun
    cron_expression: str = ""

    def validate_rule(self) -> None:
        """
        Validates the recurrence rule parameters
        """
        if self.interval < 1:
            raise ValueError("interval must be >= 1")
        
        if self.frequency == RecurrenceFrequency.WEEKLY:
            if not self.days_of_week:
                raise ValueError("days_of_week is required for weekly recurrence")
            invalid = [d for d in self.days_of_week if d not in range(7)]
            if invalid:
                raise ValueError(f"Invalid days_of_week values: {invalid} (must be 0-6)")
        
        if self.frequency == RecurrenceFrequency.CUSTOM:
            if not self.cron_expression:
                raise ValueError("cron_expression is required for custom recurrence")
            if not croniter.is_valid(self.cron_expression):
                raise ValueError(f"Invalid cron expression: {self.cron_expression!r}")

    def is_due(self, start: datetime, now: datetime, window_seconds: int = 60) -> bool:
        """
        Return True if now falls within window_seconds after the most recent
        scheduled occurrence that is >= start.
        """
        if now < start:
            return False
        
        if self.frequency == RecurrenceFrequency.CUSTOM:
            return self._is_due_cron(now, window_seconds)
        
        if self.frequency == RecurrenceFrequency.WEEKLY and self.days_of_week:
            return self._is_due_weekly(start, now, window_seconds)
        
        period = self._period_seconds()
        elapsed = (now - start).total_seconds()
        remainder = elapsed % period
        return 0 <= remainder < window_seconds

    def _period_seconds(self) -> float:
        """
        Return the recurrence period in seconds, used for non-weekly/custom frequencies.
        """
        units = {
            RecurrenceFrequency.MINUTELY: 60,
            RecurrenceFrequency.HOURLY:   3_600,
            RecurrenceFrequency.DAILY:    86_400,
            RecurrenceFrequency.WEEKLY:   7 * 86_400,
        }
        return units[self.frequency] * self.interval

    def _is_due_cron(self, now: datetime, window_seconds: int) -> bool:
        """
        Return True if now falls within window_seconds after the most recent scheduled occurrence according to the cron expression.
        """
        now_naive = now.replace(tzinfo=None)
        last = croniter(self.cron_expression, now_naive).get_prev(datetime)
        return (now_naive - last).total_seconds() < window_seconds

    def _is_due_weekly(self, start: datetime, now: datetime, window_seconds: int) -> bool:
        """Fire on specified days_of_week at the same time-of-day as start."""
        if now.weekday() not in self.days_of_week:
            return False
        
        # Check week-parity: interval=2 means every other week
        weeks_since = (now.date() - start.date()).days // 7
        if weeks_since % self.interval != 0:
            return False
        
        # Check time-of-day window
        scheduled = now.replace(
            hour=start.hour, minute=start.minute, second=start.second, microsecond=0
        )
        return 0 <= (now - scheduled).total_seconds() < window_seconds

