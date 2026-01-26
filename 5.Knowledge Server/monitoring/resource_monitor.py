#!/usr/bin/env python3
"""
MCP Knowledge Server - Resource Monitoring Script

Monitors system resources and exports metrics in Prometheus format:
- CPU usage
- Memory usage
- Disk space
- Process-specific metrics
- Database sizes
- Request/response metrics

Can run as standalone script or integrated with monitoring systems.

Usage:
    python resource_monitor.py [--interval 60] [--prometheus-port 9090] [--json] [--alert]

Exit codes:
    0: Normal operation
    1: Resource threshold exceeded
    2: Critical resource issue
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ResourceMonitor:
    """Monitor system and application resources"""

    def __init__(self, alert_thresholds: dict[str, float] | None = None):
        """
        Initialize resource monitor

        Args:
            alert_thresholds: Dictionary of threshold values for alerts
        """
        self.alert_thresholds = alert_thresholds or {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "disk_free_gb": 2.0,
        }

        # Paths
        project_dir = Path(__file__).parent.parent
        self.data_dir = project_dir / "data"
        self.event_store_path = os.getenv("EVENT_STORE_PATH", str(self.data_dir / "events.db"))
        self.chroma_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", str(self.data_dir / "chroma"))

        # Find MCP server process
        self.mcp_process = self._find_mcp_process()

    def _find_mcp_process(self) -> psutil.Process | None:
        """Find the running MCP server process"""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and "mcp_server.py" in " ".join(cmdline):
                    return psutil.Process(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def get_system_metrics(self) -> dict[str, Any]:
        """Get system-wide resource metrics"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {},
        }

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

        metrics["cpu"] = {
            "percent": cpu_percent,
            "count": cpu_count,
            "load_1min": load_avg[0],
            "load_5min": load_avg[1],
            "load_15min": load_avg[2],
        }

        # Memory metrics
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        metrics["memory"] = {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent,
        }

        # Disk metrics for data directory
        if self.data_dir.exists():
            disk = psutil.disk_usage(str(self.data_dir))
            metrics["disk"] = {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            }

        # Network I/O
        net = psutil.net_io_counters()
        metrics["network"] = {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors_in": net.errin,
            "errors_out": net.errout,
        }

        return metrics

    def get_process_metrics(self) -> dict[str, Any]:
        """Get MCP server process metrics"""
        metrics = {
            "running": False,
            "pid": None,
            "cpu_percent": 0,
            "memory_mb": 0,
            "memory_percent": 0,
            "threads": 0,
            "open_files": 0,
            "connections": 0,
        }

        if self.mcp_process is None:
            return metrics

        try:
            self.mcp_process = psutil.Process(self.mcp_process.pid)  # Refresh

            metrics["running"] = self.mcp_process.is_running()
            metrics["pid"] = self.mcp_process.pid
            metrics["cpu_percent"] = self.mcp_process.cpu_percent(interval=0.1)

            mem_info = self.mcp_process.memory_info()
            metrics["memory_mb"] = round(mem_info.rss / (1024**2), 2)
            metrics["memory_percent"] = self.mcp_process.memory_percent()

            metrics["threads"] = self.mcp_process.num_threads()
            metrics["open_files"] = len(self.mcp_process.open_files())
            metrics["connections"] = len(self.mcp_process.connections())

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return metrics

    def get_database_metrics(self) -> dict[str, Any]:
        """Get database size and growth metrics"""
        metrics = {"event_store": {}, "chromadb": {}}

        # SQLite event store metrics
        if os.path.exists(self.event_store_path):
            size_mb = os.path.getsize(self.event_store_path) / (1024**2)
            metrics["event_store"]["size_mb"] = round(size_mb, 2)

            try:
                conn = sqlite3.connect(self.event_store_path)
                cursor = conn.cursor()

                # Event counts
                event_count = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                metrics["event_store"]["event_count"] = event_count

                # Outbox metrics
                outbox_pending = cursor.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status = 'pending'"
                ).fetchone()[0]
                outbox_failed = cursor.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status = 'failed'"
                ).fetchone()[0]

                metrics["event_store"]["outbox_pending"] = outbox_pending
                metrics["event_store"]["outbox_failed"] = outbox_failed

                conn.close()
            except Exception:
                pass

        # ChromaDB metrics
        if os.path.exists(self.chroma_dir):
            total_size = 0
            for dirpath, _dirnames, filenames in os.walk(self.chroma_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

            metrics["chromadb"]["size_mb"] = round(total_size / (1024**2), 2)

        return metrics

    def check_alerts(self, metrics: dict[str, Any]) -> list[str]:
        """Check if any metrics exceed alert thresholds"""
        alerts = []

        # CPU alert
        if metrics["system"]["cpu"]["percent"] > self.alert_thresholds["cpu_percent"]:
            alerts.append(
                f"HIGH CPU: {metrics['system']['cpu']['percent']:.1f}% (threshold: {self.alert_thresholds['cpu_percent']}%)"
            )

        # Memory alert
        if metrics["system"]["memory"]["percent"] > self.alert_thresholds["memory_percent"]:
            alerts.append(
                f"HIGH MEMORY: {metrics['system']['memory']['percent']:.1f}% (threshold: {self.alert_thresholds['memory_percent']}%)"
            )

        # Disk alerts
        disk_percent = metrics["system"]["disk"].get("percent", 0)
        disk_free_gb = metrics["system"]["disk"].get("free_gb", 0)

        if disk_percent > self.alert_thresholds["disk_percent"]:
            alerts.append(
                f"HIGH DISK USAGE: {disk_percent:.1f}% (threshold: {self.alert_thresholds['disk_percent']}%)"
            )

        if disk_free_gb < self.alert_thresholds["disk_free_gb"]:
            alerts.append(
                f"LOW DISK SPACE: {disk_free_gb:.2f}GB free (threshold: {self.alert_thresholds['disk_free_gb']}GB)"
            )

        # Process not running
        if not metrics["process"]["running"]:
            alerts.append("MCP server process not running")

        # High outbox pending
        outbox_pending = metrics["database"]["event_store"].get("outbox_pending", 0)
        if outbox_pending > 100:
            alerts.append(f"HIGH OUTBOX PENDING: {outbox_pending} items")

        return alerts

    def generate_prometheus_metrics(self, metrics: dict[str, Any]) -> str:
        """Generate Prometheus-format metrics"""
        lines = []

        # System CPU
        lines.append("# HELP mcp_cpu_percent CPU usage percentage")
        lines.append("# TYPE mcp_cpu_percent gauge")
        lines.append(f"mcp_cpu_percent {metrics['system']['cpu']['percent']}")

        # System memory
        lines.append("# HELP mcp_memory_percent Memory usage percentage")
        lines.append("# TYPE mcp_memory_percent gauge")
        lines.append(f"mcp_memory_percent {metrics['system']['memory']['percent']}")

        # Disk
        lines.append("# HELP mcp_disk_percent Disk usage percentage")
        lines.append("# TYPE mcp_disk_percent gauge")
        lines.append(f"mcp_disk_percent {metrics['system']['disk'].get('percent', 0)}")

        lines.append("# HELP mcp_disk_free_gb Free disk space in GB")
        lines.append("# TYPE mcp_disk_free_gb gauge")
        lines.append(f"mcp_disk_free_gb {metrics['system']['disk'].get('free_gb', 0)}")

        # Process
        lines.append("# HELP mcp_process_running MCP server process running (1=yes, 0=no)")
        lines.append("# TYPE mcp_process_running gauge")
        lines.append(f"mcp_process_running {1 if metrics['process']['running'] else 0}")

        lines.append("# HELP mcp_process_cpu_percent Process CPU usage percentage")
        lines.append("# TYPE mcp_process_cpu_percent gauge")
        lines.append(f"mcp_process_cpu_percent {metrics['process']['cpu_percent']}")

        lines.append("# HELP mcp_process_memory_mb Process memory usage in MB")
        lines.append("# TYPE mcp_process_memory_mb gauge")
        lines.append(f"mcp_process_memory_mb {metrics['process']['memory_mb']}")

        # Database
        event_count = metrics["database"]["event_store"].get("event_count", 0)
        lines.append("# HELP mcp_event_store_events Total events in event store")
        lines.append("# TYPE mcp_event_store_events counter")
        lines.append(f"mcp_event_store_events {event_count}")

        outbox_pending = metrics["database"]["event_store"].get("outbox_pending", 0)
        lines.append("# HELP mcp_outbox_pending Pending items in outbox")
        lines.append("# TYPE mcp_outbox_pending gauge")
        lines.append(f"mcp_outbox_pending {outbox_pending}")

        db_size = metrics["database"]["event_store"].get("size_mb", 0)
        lines.append("# HELP mcp_database_size_mb Database size in MB")
        lines.append("# TYPE mcp_database_size_mb gauge")
        lines.append(f'mcp_database_size_mb{{database="event_store"}} {db_size}')

        chroma_size = metrics["database"]["chromadb"].get("size_mb", 0)
        lines.append(f'mcp_database_size_mb{{database="chromadb"}} {chroma_size}')

        return "\n".join(lines)

    def collect_metrics(self) -> dict[str, Any]:
        """Collect all metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": self.get_system_metrics(),
            "process": self.get_process_metrics(),
            "database": self.get_database_metrics(),
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Knowledge Server Resource Monitor")
    parser.add_argument(
        "--interval", type=int, default=60, help="Monitoring interval in seconds (0 for one-time)"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--prometheus", action="store_true", help="Output in Prometheus format")
    parser.add_argument("--alert", action="store_true", help="Check alert thresholds")

    args = parser.parse_args()

    monitor = ResourceMonitor()

    def collect_and_output():
        """Collect metrics and output in requested format"""
        metrics = monitor.collect_metrics()

        if args.prometheus:
            print(monitor.generate_prometheus_metrics(metrics))
        elif args.json:
            print(json.dumps(metrics, indent=2))
        else:
            # Human-readable output
            print(f"\nMCP Resource Monitor - {metrics['timestamp']}")
            print("=" * 60)

            # System
            sys_metrics = metrics["system"]
            print("\nSystem Resources:")
            print(
                f"  CPU: {sys_metrics['cpu']['percent']:.1f}% ({sys_metrics['cpu']['count']} cores)"
            )
            print(
                f"  Memory: {sys_metrics['memory']['used_gb']:.2f}GB / {sys_metrics['memory']['total_gb']:.2f}GB ({sys_metrics['memory']['percent']:.1f}%)"
            )
            print(
                f"  Disk: {sys_metrics['disk'].get('used_gb', 0):.2f}GB / {sys_metrics['disk'].get('total_gb', 0):.2f}GB ({sys_metrics['disk'].get('percent', 0):.1f}%)"
            )

            # Process
            proc_metrics = metrics["process"]
            if proc_metrics["running"]:
                print(f"\nMCP Server Process (PID {proc_metrics['pid']}):")
                print(f"  CPU: {proc_metrics['cpu_percent']:.1f}%")
                print(
                    f"  Memory: {proc_metrics['memory_mb']:.2f}MB ({proc_metrics['memory_percent']:.1f}%)"
                )
                print(f"  Threads: {proc_metrics['threads']}")
                print(f"  Open Files: {proc_metrics['open_files']}")
            else:
                print("\n⚠️  MCP Server Process: NOT RUNNING")

            # Database
            db_metrics = metrics["database"]
            print("\nDatabase Metrics:")
            if "event_count" in db_metrics["event_store"]:
                print(
                    f"  Event Store: {db_metrics['event_store']['event_count']} events ({db_metrics['event_store']['size_mb']:.2f}MB)"
                )
                print(
                    f"  Outbox: {db_metrics['event_store'].get('outbox_pending', 0)} pending, {db_metrics['event_store'].get('outbox_failed', 0)} failed"
                )
            if "size_mb" in db_metrics["chromadb"]:
                print(f"  ChromaDB: {db_metrics['chromadb']['size_mb']:.2f}MB")

            print()

        # Check alerts
        if args.alert:
            alerts = monitor.check_alerts(metrics)
            if alerts:
                print("\n🚨 ALERTS:")
                for alert in alerts:
                    print(f"  - {alert}")
                print()
                return 1
            else:
                print("✅ No alerts\n")

        return 0

    # Run monitoring loop or one-time
    if args.interval > 0:
        print(f"Monitoring every {args.interval} seconds (Ctrl+C to stop)...")
        try:
            while True:
                exit_code = collect_and_output()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            sys.exit(0)
    else:
        exit_code = collect_and_output()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
