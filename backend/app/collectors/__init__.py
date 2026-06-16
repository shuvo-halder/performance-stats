from app.collectors.system import collect_system_info
from app.collectors.cpu import collect_cpu_info
from app.collectors.memory import collect_memory_info
from app.collectors.disk import collect_disk_info
from app.collectors.network import collect_network_info
from app.collectors.services import collect_services_info
from app.collectors.processes import collect_top_processes
from app.collectors.security import collect_security_info


async def collect_all_metrics():
    """Collect all system metrics and return as a dictionary matching Snapshot model."""
    import asyncio

    # Run all collectors concurrently
    system = await collect_system_info()
    cpu = await collect_cpu_info()
    memory = await collect_memory_info()
    disk = await collect_disk_info()
    network = await collect_network_info()
    services = await collect_services_info()
    processes = await collect_top_processes()
    security = await collect_security_info()

    return {
        **system,
        **cpu,
        **memory,
        **disk,
        **network,
        **services,
        **processes,
        **security,
    }