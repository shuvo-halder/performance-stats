import psutil
from typing import Dict


async def collect_memory_info() -> Dict:
    """Collect memory usage information including swap."""
    mem = psutil.virtual_memory()
    total_mb = round(mem.total / (1024 * 1024), 2)
    used_mb = round(mem.used / (1024 * 1024), 2)
    free_mb = round(mem.available / (1024 * 1024), 2)
    usage_percent = round(mem.percent, 2)

    # Swap memory
    try:
        swap = psutil.swap_memory()
        swap_total_mb = round(swap.total / (1024 * 1024), 2)
        swap_used_mb = round(swap.used / (1024 * 1024), 2)
        swap_percent = round(swap.percent, 2)
    except Exception:
        swap_total_mb = 0
        swap_used_mb = 0
        swap_percent = 0

    return {
        "mem_total_mb": total_mb,
        "mem_used_mb": used_mb,
        "mem_free_mb": free_mb,
        "mem_usage_percent": usage_percent,
        "swap_total_mb": swap_total_mb,
        "swap_used_mb": swap_used_mb,
        "swap_percent": swap_percent,
    }
