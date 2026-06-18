from app.collectors.system import collect_system_info
from app.collectors.cpu import collect_cpu_info
from app.collectors.memory import collect_memory_info
from app.collectors.disk import collect_disk_info
from app.collectors.network import collect_network_info
from app.collectors.services import collect_services_info
from app.collectors.processes import collect_top_processes
from app.collectors.security import collect_security_info


async def collect_all_metrics(timeout: float = 10.0):
    """Collect all system metrics concurrently with a timeout.

    Returns partial results if a collector times out — ensures the dashboard
    never hangs on slow operations.
    """
    import asyncio

    # Define all collector tasks with timeouts
    async def run_with_timeout(coro, name: str):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            print(f"[WARN] Collector '{name}' timed out after {timeout}s")
            return {}

    # Run all collectors concurrently with individual timeouts
    results = await asyncio.gather(
        run_with_timeout(collect_system_info(), "system"),
        run_with_timeout(collect_cpu_info(), "cpu"),
        run_with_timeout(collect_memory_info(), "memory"),
        run_with_timeout(collect_disk_info(), "disk"),
        run_with_timeout(collect_network_info(), "network"),
        run_with_timeout(collect_services_info(), "services"),
        run_with_timeout(collect_top_processes(), "processes"),
        run_with_timeout(collect_security_info(), "security"),
        return_exceptions=True,
    )

    metrics = {}
    auto_restart_results = []

    for result in results:
        if isinstance(result, dict):
            if "auto_restart_results" in result:
                auto_restart_results = result.pop("auto_restart_results", [])
            metrics.update(result)

    return metrics, auto_restart_results
