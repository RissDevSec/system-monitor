"""Entrypoint for the system monitor."""

from __future__ import annotations

import time

import psutil
from dotenv import load_dotenv
from loguru import logger

from alerts import AlertTracker
from config import ConfigError, load_config
from logger_config import setup_logger
from messages import format_alert, format_status
from metrics import (
    MetricReading,
    MetricSpec,
    SystemMetricsCollector,
    build_metric_specs,
)
from notifier import TelegramError, TelegramNotifier


def check_once(
    collector: SystemMetricsCollector,
    specs: tuple[MetricSpec, ...],
    alerts: AlertTracker,
    notifier: TelegramNotifier,
) -> dict[str, MetricReading]:
    """Collect one reading, deliver pending alerts, and log the status."""
    readings = collector.collect(specs)
    warnings = {key: reading.is_warning for key, reading in readings.items()}
    pending = alerts.pending(warnings)

    if pending:
        if alerts.backing_off():
            # A previous delivery failed; wait for the backoff window before
            # trying again instead of hammering Telegram on every check.
            pass
        else:
            message = format_alert(readings, pending)
            summary = message.strip().replace("\n", " | ")

            try:
                notifier.send(message)
            except TelegramError as error:
                if not error.retryable:
                    alerts.abandon(pending)
                    logger.critical(
                        "Failed to send Telegram notification ({}): {}. This error is "
                        "permanent; the alert will not be retried until the next state "
                        "change. Check BOT_KEY/CHAT_ID and the bot's access to the chat.",
                        summary,
                        error,
                    )
                else:
                    attempt, delay = alerts.failed(error.retry_after)
                    logger.error(
                        "Failed to send Telegram notification ({}): {}. Attempt {} failed; "
                        "next try in at least {}s.",
                        summary,
                        error,
                        attempt,
                        delay,
                    )
            else:
                failures = alerts.delivered(pending)
                if failures:
                    logger.info(
                        "Telegram notification ({}) delivered after {} failed attempt(s).",
                        summary,
                        failures,
                    )
    elif alerts.failures:
        # The situation went back to what the last delivered message already
        # says, so the undelivered alert is no longer useful.
        logger.info(
            "Dropped the undelivered alert: the situation is back to "
            "what you were last told."
        )
        alerts.forget_failures()

    status = format_status(readings)
    if any(warnings.values()):
        logger.warning(status)
    else:
        logger.info(status)

    return readings


def main() -> int:
    load_dotenv()
    setup_logger()

    try:
        config = load_config()
    except ConfigError as error:
        logger.error("Invalid configuration: {}", error)
        return 1

    specs = build_metric_specs(config)
    collector = SystemMetricsCollector(config.procfs_path, config.disk_path)
    alerts = AlertTracker([spec.key for spec in specs], config.repeat_interval)
    notifier = TelegramNotifier(config.bot_key, config.chat_id)

    reminders = f"every {config.repeat_interval}s" if config.repeat_interval else "off"
    logger.info(
        "System monitor started - interval: {}s | thresholds CPU/RAM/Disk: "
        "{}%/{}%/{}% | reminders: {}",
        config.check_interval,
        config.cpu_threshold,
        config.ram_threshold,
        config.disk_threshold,
        reminders,
    )

    try:
        # cpu_percent() reports the average since its previous call. Prime the
        # sampler once so the first real reading covers a short window instead
        # of always starting at 0%.
        collector.prime_cpu()
        time.sleep(1)

        next_check = time.monotonic()

        while True:
            wait = next_check - time.monotonic()
            if wait > 0:
                time.sleep(wait)

            started = time.monotonic()

            try:
                check_once(collector, specs, alerts, notifier)
            except (psutil.Error, OSError) as error:
                logger.error("Check failed, retrying next cycle: {}", error)

            next_check = max(next_check + config.check_interval, started)
    except KeyboardInterrupt:
        logger.info("Stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
