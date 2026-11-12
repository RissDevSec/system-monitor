"""Metric definitions and host metric collection."""

from __future__ import annotations

from dataclasses import dataclass

import psutil

from config import Config

BYTES_PER_GIB = 1024**3


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    threshold: int
    warning_description: str


@dataclass(frozen=True)
class MetricReading:
    spec: MetricSpec
    percent: float
    display: str

    @property
    def is_warning(self) -> bool:
        # Compare the raw value, not the rounded display value. A metric at
        # 79.6% should not fire an 80% threshold just because it displays as 80%.
        return self.percent >= self.spec.threshold


def build_metric_specs(config: Config) -> tuple[MetricSpec, ...]:
    return (
        MetricSpec("cpu", "CPU", config.cpu_threshold, "under heavy load"),
        MetricSpec("ram", "RAM", config.ram_threshold, "almost full"),
        MetricSpec("disk", "Disk", config.disk_threshold, "almost full"),
    )


class SystemMetricsCollector:
    """Read CPU, RAM, and disk stats from the configured host paths."""

    def __init__(self, procfs_path: str, disk_path: str):
        self._disk_path = disk_path
        psutil.PROCFS_PATH = procfs_path

    def prime_cpu(self) -> None:
        """Start a CPU sampling window; the next call reports its average."""
        psutil.cpu_percent()

    def collect(self, specs: tuple[MetricSpec, ...]) -> dict[str, MetricReading]:
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(self._disk_path)

        raw_percent = {
            "cpu": psutil.cpu_percent(),
            "ram": ram.percent,
            "disk": disk.percent,
        }

        readings: dict[str, MetricReading] = {}
        for spec in specs:
            percent = raw_percent[spec.key]
            detail = ""

            if spec.key == "ram":
                # Derive the detail from the same basis as ram.percent so the
                # percentage and the GB numbers do not contradict each other.
                used = ram.total - ram.available
                detail = (
                    f" ({used / BYTES_PER_GIB:.1f}/{ram.total / BYTES_PER_GIB:.1f} GB)"
                )

            readings[spec.key] = MetricReading(
                spec=spec,
                percent=percent,
                display=f"{round(percent)}%{detail}",
            )

        return readings
