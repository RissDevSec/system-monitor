"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(ValueError):
    """Raised when the monitor configuration is invalid."""


@dataclass(frozen=True)
class Config:
    procfs_path: str
    disk_path: str
    cpu_threshold: int
    ram_threshold: int
    disk_threshold: int
    check_interval: int
    repeat_interval: int
    bot_key: str = field(repr=False)
    chat_id: str = field(repr=False)


def _env_text(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = os.getenv(name, str(default))

    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be a number, got '{raw}'") from error

    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be at most {maximum}, got {value}")

    return value


def _validate_directory(name: str, path: str) -> None:
    if not os.path.isdir(path):
        raise ConfigError(f"{name} is not a directory: {path}")


def _validate_procfs(path: str) -> None:
    _validate_directory("PROCFS_PATH", path)

    # psutil reads these two files for CPU and memory stats. Checking them here
    # turns a missing host mount into a clear startup error instead of a crash
    # in the first check.
    for filename in ("stat", "meminfo"):
        if not os.path.isfile(os.path.join(path, filename)):
            raise ConfigError(
                f"PROCFS_PATH does not look like a procfs: missing {filename} in {path}"
            )


def load_config() -> Config:
    bot_key = _env_text("BOT_KEY", "")
    chat_id = _env_text("CHAT_ID", "")

    if not bot_key or not chat_id:
        raise ConfigError("BOT_KEY and CHAT_ID must be set")

    config = Config(
        procfs_path=_env_text("PROCFS_PATH", "/proc"),
        disk_path=_env_text("DISK_PATH", "/"),
        cpu_threshold=_env_int("CPU_THRESHOLD", 80, minimum=1, maximum=100),
        ram_threshold=_env_int("RAM_THRESHOLD", 80, minimum=1, maximum=100),
        disk_threshold=_env_int("DISK_THRESHOLD", 80, minimum=1, maximum=100),
        check_interval=_env_int("CHECK_INTERVAL", 60, minimum=1),
        repeat_interval=_env_int("REPEAT_INTERVAL", 14400, minimum=0),
        bot_key=bot_key,
        chat_id=chat_id,
    )

    _validate_procfs(config.procfs_path)
    _validate_directory("DISK_PATH", config.disk_path)

    return config
