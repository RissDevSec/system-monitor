"""Entrypoint for the system monitor."""

from __future__ import annotations

import time

import psutil
from dotenv import load_dotenv
from loguru import logger

from config import ConfigError, load_config
from logger_config import setup_logger
from metrics import (
    MetricReading,
    MetricSpec,
    SystemMetricsCollector,
    build_metric_specs,
)
from notifier import message_warning

WARNING_ICON = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"
OK_ICON = "\N{WHITE HEAVY CHECK MARK}"


def check_once(
    collector: SystemMetricsCollector,
    specs: tuple[MetricSpec, ...],
    state: dict[str, bool],
) -> dict[str, MetricReading]:
    """Collect one reading and notify only when a metric changes state."""
    readings = collector.collect(specs)
    message = ""

    for key, reading in readings.items():
        if reading.is_warning and not state[key]:
            message += (
                f"{WARNING_ICON} WARNING - {reading.spec.label} "
                f"{reading.spec.warning_description}! "
                f"({round(reading.percent)}%)\n"
            )
            state[key] = True
        elif not reading.is_warning and state[key]:
            message += f"{OK_ICON} INFO - {reading.spec.label} back to normal\n"
            state[key] = False

    if message:
        message_warning(message)

    return readings


def format_status(readings: dict[str, MetricReading]) -> str:
    parts = []

    for reading in readings.values():
        value = reading.display
        if reading.is_warning:
            value += " WARNING"
        parts.append(f"{reading.spec.label}: {value}")

    return " | ".join(parts)


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
    state = {spec.key: False for spec in specs}

    logger.info(
        "System monitor started - interval: {}s | thresholds CPU/RAM/Disk: "
        "{}%/{}%/{}%",
        config.check_interval,
        config.cpu_threshold,
        config.ram_threshold,
        config.disk_threshold,
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
                readings = check_once(collector, specs, state)
                status = format_status(readings)

                if any(reading.is_warning for reading in readings.values()):
                    logger.warning(status)
                else:
                    logger.info(status)
            except (psutil.Error, OSError) as error:
                logger.error("Check failed, retrying next cycle: {}", error)

            next_check = max(next_check + config.check_interval, started)
    except KeyboardInterrupt:
        logger.info("Stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
