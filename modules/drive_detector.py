from __future__ import annotations

from pathlib import Path

import psutil


def find_camera_sources() -> list[str]:
    sources: list[str] = []
    for partition in psutil.disk_partitions(all=False):
        try:
            mount = Path(partition.mountpoint)
            dcim = mount / "DCIM"
            if dcim.is_dir():
                sources.append(str(dcim))
        except (OSError, PermissionError):
            continue
    return list(dict.fromkeys(sources))
