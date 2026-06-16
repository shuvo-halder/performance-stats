import psutil
from typing import Dict


async def collect_network_info() -> Dict:
    """Collect network connections and listening ports."""
    connections_count = len(psutil.net_connections())
    listening_ports = []

    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN":
                port_info = {
                    "port": conn.laddr.port,
                    "address": conn.laddr.ip,
                }
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        port_info["process"] = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        port_info["process"] = "unknown"
                else:
                    port_info["process"] = "unknown"
                listening_ports.append(port_info)
    except (psutil.AccessDenied, PermissionError):
        listening_ports = [{"port": "N/A", "address": "N/A", "process": "Permission denied"}]

    return {
        "network_connections": connections_count,
        "network_listening_ports": listening_ports[:20],  # Limit to top 20
    }