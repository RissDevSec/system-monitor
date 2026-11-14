"""Formatting for log lines and Telegram alerts."""

from __future__ import annotations

from typing import Mapping

from alerts import AlertKind
from metrics import MetricReading


def format_status(readings: Mapping[str, MetricReading]) -> str:
    parts = []

    for reading in readings.values():
        value = reading.display
        if reading.is_warning:
            value += " \N{WARNING SIGN} WARNING"
        parts.append(f"{reading.spec.label}: {value}")

    return " | ".join(parts)


def format_alert(
    readings: Mapping[str, MetricReading],
    pending: Mapping[str, AlertKind],
) -> str:
    lines = []

    for key, kind in pending.items():
        reading = readings[key]
        label = reading.spec.label
        description = reading.spec.warning_description
        percent = round(reading.percent)

        if kind == AlertKind.FIRING:
            lines.append(f"⚠️ WARNING - {label} {description}! ({percent}%)")
        elif kind == AlertKind.REMINDER:
            lines.append(
                f"⚠️ STILL WARNING - {label} is still {description} ({percent}%)"
            )
        else:
            lines.append(f"✅ INFO - {label} back to normal")

    return "\n".join(lines) + "\n"
