import asyncio
import platform
from typing import Dict
from app.config import settings


async def collect_services_info() -> Dict:
    """Collect systemd service status. Falls back gracefully on non-Linux."""
    services_data = []
    auto_restart_results = []
    is_linux = platform.system() == "Linux"

    for svc in settings.services_list:
        status = "unknown"

        if is_linux:
            try:
                # Check via systemctl
                proc = await asyncio.create_subprocess_exec(
                    "systemctl", "is-active", svc,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                status = stdout.decode().strip() if stdout else "unknown"

                # If inactive and auto-restart enabled
                if status != "active" and settings.auto_restart_failed_services:
                    restart_ok = await _restart_service(svc)
                    auto_restart_results.append({
                        "service": svc,
                        "restarted": restart_ok,
                    })
                    if restart_ok:
                        status = "active (restarted)"
            except FileNotFoundError:
                # systemctl not available (e.g. running inside Docker without host systemd access)
                status = "unavailable (container)"
        else:
            # Non-Linux: check if process is running via psutil
            import psutil
            running = False
            for proc in psutil.process_iter(["name"]):
                try:
                    if svc.lower() in proc.info["name"].lower():
                        running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            status = "running" if running else "not found"

        services_data.append({
            "name": svc,
            "status": status,
        })

    return {
        "services_data": services_data,
        "auto_restart_results": auto_restart_results,
    }


async def _restart_service(svc: str) -> bool:
    """Attempt to restart a service with retry logic."""
    for attempt in range(1, settings.restart_attempts + 1):
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", svc,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode == 0:
            await asyncio.sleep(settings.restart_delay)
            # Verify it's running
            check = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", svc,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await check.communicate()
            if stdout.decode().strip() == "active":
                return True

        if attempt < settings.restart_attempts:
            await asyncio.sleep(settings.restart_delay)

    return False