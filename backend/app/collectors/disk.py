import psutil
from typing import Dict


async def collect_disk_info() -> Dict:
    """Collect disk usage per mount point."""
    disk_data = []
    for partition in psutil.disk_partitions():
        # Skip pseudo filesystems
        if partition.fstype in ("tmpfs", "devtmpfs", "squashfs", "overlay", "proc", "sysfs", "cgroup", "cgroup2", "devpts", "hugetlbfs", "mqueue", "pstore", "securityfs", "efivarfs"):
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_data.append({
                "mount": partition.mountpoint,
                "device": partition.device,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_percent": usage.percent,
            })
        except PermissionError:
            continue

    return {
        "disk_data": disk_data,
    }