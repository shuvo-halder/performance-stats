import asyncio
import platform
from typing import Dict


async def collect_security_info() -> Dict:
    """Collect failed SSH login attempts and open ports."""
    failed_logins = 0

    # Failed SSH login attempts (Linux only - reads auth.log)
    if platform.system() == "Linux":
        auth_logs = [
            "/var/log/auth.log",
            "/var/log/secure",
        ]
        for log_path in auth_logs:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "grep", "Failed password", log_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    failed_logins = len(stdout.decode().strip().split("\n"))
                break
            except FileNotFoundError:
                # grep binary not found or log file missing (e.g. inside Docker)
                continue
            except Exception:
                continue

    return {
        "failed_logins": failed_logins,
    }