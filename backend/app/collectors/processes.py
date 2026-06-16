import psutil
from typing import Dict


async def collect_top_processes() -> Dict:
    """Collect top CPU and memory consuming processes."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            pinfo = proc.info
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU descending, take top 5
    top_cpu = sorted(processes, key=lambda p: p.get("cpu_percent", 0) or 0, reverse=True)[:5]
    # Sort by memory descending, take top 5
    top_mem = sorted(processes, key=lambda p: p.get("memory_percent", 0) or 0, reverse=True)[:5]

    def format_proc(p):
        return {
            "pid": p["pid"],
            "name": p["name"],
            "cpu_percent": round(p.get("cpu_percent", 0) or 0, 1),
            "mem_percent": round(p.get("memory_percent", 0) or 0, 1),
        }

    return {
        "top_cpu_processes": [format_proc(p) for p in top_cpu],
        "top_mem_processes": [format_proc(p) for p in top_mem],
    }