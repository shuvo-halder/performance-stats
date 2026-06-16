import platform
import psutil
from typing import Dict


async def collect_system_info() -> Dict:
    """Collect OS, kernel, hostname, and uptime information."""
    hostname = platform.node()
    os_name = f"{platform.system()} {platform.release()}"
    kernel = platform.version()

    # Uptime via psutil (cross-platform)
    boot_time = psutil.boot_time()
    import time
    seconds = int(time.time() - boot_time)
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)

    if days > 0:
        uptime = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime = f"{hours}h {minutes}m"
    else:
        uptime = f"{minutes}m"

    return {
        "hostname": hostname,
        "os_name": os_name,
        "kernel": kernel,
        "uptime": uptime,
    }