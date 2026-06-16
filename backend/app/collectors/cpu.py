import psutil
import os
from typing import Dict


async def collect_cpu_info() -> Dict:
    """Collect CPU cores, usage percentage, and load averages."""
    cores = psutil.cpu_count(logical=True) or 1
    usage_percent = psutil.cpu_percent(interval=0.5)

    # Load average - different on Windows vs Unix
    load_1min = 0.0
    load_5min = 0.0
    load_15min = 0.0
    try:
        load_avg = os.getloadavg()
        load_1min, load_5min, load_15min = load_avg
    except (AttributeError, OSError):
        # Windows doesn't have getloadavg(), approximate from CPU usage
        load_1min = usage_percent / 100.0
        load_5min = usage_percent / 100.0
        load_15min = usage_percent / 100.0

    return {
        "cpu_cores": cores,
        "cpu_usage_percent": round(usage_percent, 2),
        "cpu_load_1min": round(load_1min, 2),
        "cpu_load_5min": round(load_5min, 2),
        "cpu_load_15min": round(load_15min, 2),
    }