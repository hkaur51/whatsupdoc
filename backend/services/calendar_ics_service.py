"""
Generate ICS (iCalendar) content for appointments so patients/doctors can add to phone calendar.
No Google Calendar - calendar is stored in DB; this exports events for device calendar.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# India standard time offset for ICS (phone will show correct local time)
INDIA_TZ = timezone(timedelta(hours=5, minutes=30))


def format_ics_datetime_utc(dt: datetime) -> str:
    """Format datetime for ICS DTSTAMP (UTC)."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def generate_ics_for_appointment(
    appointment_id: str,
    summary: str,
    start_date: str,
    start_time: str,
    duration_minutes: int = 30,
    description: Optional[str] = None,
) -> str:
    """
    Generate ICS file content for one appointment.
    start_date: YYYY-MM-DD, start_time: HH:MM. Uses Asia/Kolkata so phone shows correct local time.
    """
    try:
        if ":" in start_time and len(start_time) <= 5:
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        else:
            start_dt = datetime.strptime(f"{start_date} 09:00", "%Y-%m-%d %H:%M")
    except ValueError:
        start_dt = datetime.strptime(f"{start_date} 09:00", "%Y-%m-%d %H:%M")
    start_dt = start_dt.replace(tzinfo=INDIA_TZ)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    desc = description or f"DentBot appointment {appointment_id}"
    summary_safe = summary.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    desc_safe = desc.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    # DTSTART/DTEND with TZID so phone calendar shows correct local time
    def format_local(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%S")
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DentBot//EN",
        "BEGIN:VEVENT",
        f"UID:dentbot-{appointment_id}@dentbot",
        f"DTSTAMP:{format_ics_datetime_utc(datetime.now(timezone.utc))}",
        "DTSTART;TZID=Asia/Kolkata:" + format_local(start_dt),
        "DTEND;TZID=Asia/Kolkata:" + format_local(end_dt),
        f"SUMMARY:{summary_safe}",
        f"DESCRIPTION:{desc_safe}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(ics)
