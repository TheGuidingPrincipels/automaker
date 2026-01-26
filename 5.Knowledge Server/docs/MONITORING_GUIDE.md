# MCP Knowledge Server - Comprehensive Monitoring Guide

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Philosophy](#monitoring-philosophy)
3. [Health Check System](#health-check-system)
4. [Resource Monitoring](#resource-monitoring)
5. [Service Monitoring with Auto-Restart](#service-monitoring-with-auto-restart)
6. [Prometheus Integration](#prometheus-integration)
7. [Grafana Dashboard Setup](#grafana-dashboard-setup)
8. [Alert Thresholds and Notifications](#alert-thresholds-and-notifications)
9. [Metrics Reference](#metrics-reference)
10. [Log Aggregation and Analysis](#log-aggregation-and-analysis)
11. [Performance Monitoring Best Practices](#performance-monitoring-best-practices)
12. [Troubleshooting with Monitoring Data](#troubleshooting-with-monitoring-data)

---

## Overview

The MCP Knowledge Server includes a comprehensive monitoring suite designed to ensure reliability, performance, and operational visibility. The monitoring system provides:

- **Health Checks**: Validate all components are functioning correctly
- **Resource Monitoring**: Track CPU, memory, disk, and network usage
- **Service Monitoring**: Ensure the server is running and auto-restart if needed
- **Metrics Export**: Integration with Prometheus, Grafana, and other tools
- **Alerting**: Proactive notifications when thresholds are exceeded

### Monitoring Components

```
monitoring/
├── health_check.py          # Comprehensive health validation
├── resource_monitor.py      # System and application metrics
└── service_monitor.sh       # Process monitoring and auto-restart
```

---

## Monitoring Philosophy

### Core Principles

1. **Proactive Detection**: Identify issues before they impact users
2. **Comprehensive Coverage**: Monitor all critical components
3. **Actionable Metrics**: Focus on metrics that inform decisions
4. **Automated Recovery**: Auto-restart services when appropriate
5. **Historical Analysis**: Maintain metrics for trend analysis

### What We Monitor

- **Infrastructure**: CPU, memory, disk, network
- **Database Health**: Neo4j, SQLite event store, ChromaDB
- **Application Performance**: Latency, throughput, error rates
- **Business Metrics**: Event counts, concept storage, vector operations

### Monitoring Levels

1. **L1 - Critical**: Service availability, database connectivity
2. **L2 - Important**: Resource thresholds, performance degradation
3. **L3 - Informational**: Growth trends, usage patterns

---

## Health Check System

### Overview

The health check script (`health_check.py`) performs comprehensive validation of all MCP server components.

### Usage

```bash
# Basic health check
python monitoring/health_check.py

# Verbose output
python monitoring/health_check.py --verbose

# JSON output (for monitoring tools)
python monitoring/health_check.py --json

# Include write capability tests
python monitoring/health_check.py --check-write
```

### Exit Codes

- `0`: All checks passed (healthy)
- `1`: One or more checks failed (degraded)
- `2`: Critical failure (system unusable)

### Checks Performed

#### 1. Neo4j Database Check

**Purpose**: Validate graph database connectivity and performance

**Metrics**:

- Connection latency (ms)
- Database version and edition
- Write capability (optional)
- Concept count

**Success Criteria**:

- Connection established within 5 seconds
- Database responds to queries
- Write test succeeds (if enabled)

**Example**:

```bash
python monitoring/health_check.py --check-write --verbose
```

#### 2. SQLite Event Store Check

**Purpose**: Ensure event sourcing system integrity

**Metrics**:

- File existence and size
- Database integrity
- Event count
- Outbox pending items

**Success Criteria**:

- Database file exists and is accessible
- PRAGMA integrity_check returns "ok"
- Outbox pending count < 100 (otherwise degraded)

**Alert Conditions**:

- File missing: CRITICAL
- Integrity check failed: CRITICAL
- Outbox pending > 100: WARNING

#### 3. ChromaDB Vector Database Check

**Purpose**: Validate vector search capability

**Metrics**:

- Directory existence and size
- Collection list
- Concept count in vectors

**Success Criteria**:

- ChromaDB directory accessible
- Can list collections
- Concept collection accessible

#### 4. Disk Space Check

**Purpose**: Prevent data directory exhaustion

**Metrics**:

- Total, used, and free space (GB)
- Percentage used

**Alert Thresholds**:

- Free < 1GB: CRITICAL
- Usage > 90%: WARNING

### JSON Output Format

```json
{
  "timestamp": "2025-10-07T12:00:00Z",
  "overall_status": "healthy",
  "checks": {
    "neo4j": {
      "status": "healthy",
      "message": "Neo4j connection successful",
      "latency_ms": 45.2,
      "concept_count": 1250,
      "database_info": {
        "name": "neo4j",
        "versions": ["5.13.0"],
        "edition": "community"
      }
    },
    "sqlite": {
      "status": "healthy",
      "message": "Event store healthy",
      "file_exists": true,
      "file_size_mb": 12.5,
      "integrity": "ok",
      "event_count": 5420,
      "outbox_pending": 3
    },
    "chromadb": {
      "status": "healthy",
      "message": "ChromaDB accessible",
      "directory_exists": true,
      "directory_size_mb": 45.8,
      "collections": ["concepts"],
      "concept_count": 1250
    },
    "disk_space": {
      "status": "healthy",
      "message": "Sufficient disk space",
      "data_directory": {
        "total_gb": 500.0,
        "used_gb": 125.3,
        "free_gb": 374.7,
        "percent_used": 25.1
      }
    }
  }
}
```

### Integration with Monitoring Systems

#### Nagios/Icinga

```bash
# /etc/nagios/commands.cfg
define command {
    command_name    check_mcp_health
    command_line    /path/to/mcp-knowledge-server/monitoring/health_check.py --json
}

# Service definition
define service {
    service_description     MCP Server Health
    check_command           check_mcp_health
    check_interval          5
    retry_interval          1
}
```

#### Cron-based Monitoring

```bash
# Check health every 5 minutes
*/5 * * * * /path/to/mcp-knowledge-server/monitoring/health_check.py --json >> /var/log/mcp-health.log 2>&1
```

---

## Resource Monitoring

### Overview

The resource monitor (`resource_monitor.py`) tracks system and application resource usage, exporting metrics in multiple formats.

### Usage

```bash
# One-time check (human-readable)
python monitoring/resource_monitor.py --interval 0

# Continuous monitoring every 60 seconds
python monitoring/resource_monitor.py --interval 60

# JSON output
python monitoring/resource_monitor.py --interval 0 --json

# Prometheus format
python monitoring/resource_monitor.py --interval 0 --prometheus

# Enable alerting
python monitoring/resource_monitor.py --interval 0 --alert
```

### Metrics Collected

#### System Metrics

**CPU**:

- `cpu_percent`: Overall CPU usage percentage
- `cpu_count`: Number of CPU cores
- `load_1min`, `load_5min`, `load_15min`: System load averages

**Memory**:

- `total_gb`: Total RAM
- `available_gb`: Available RAM
- `used_gb`: Used RAM
- `percent`: Memory usage percentage
- `swap_total_gb`, `swap_used_gb`, `swap_percent`: Swap metrics

**Disk**:

- `total_gb`: Total disk space
- `used_gb`: Used disk space
- `free_gb`: Free disk space
- `percent`: Disk usage percentage

**Network**:

- `bytes_sent_mb`, `bytes_recv_mb`: Network throughput
- `packets_sent`, `packets_recv`: Packet counts
- `errors_in`, `errors_out`: Network errors

#### Process Metrics

**MCP Server Process**:

- `running`: Boolean indicating if process is active
- `pid`: Process ID
- `cpu_percent`: Process CPU usage
- `memory_mb`: Process memory usage (MB)
- `memory_percent`: Process memory percentage
- `threads`: Thread count
- `open_files`: Open file descriptor count
- `connections`: Active network connections

#### Database Metrics

**Event Store**:

- `size_mb`: SQLite database file size
- `event_count`: Total events stored
- `outbox_pending`: Pending outbox items
- `outbox_failed`: Failed outbox items

**ChromaDB**:

- `size_mb`: Total vector database size

### Alert Thresholds

Default thresholds (configurable):

```python
alert_thresholds = {
    "cpu_percent": 80.0,        # 80% CPU usage
    "memory_percent": 85.0,     # 85% memory usage
    "disk_percent": 90.0,       # 90% disk usage
    "disk_free_gb": 2.0        # 2GB minimum free
}
```

### Custom Threshold Configuration

```python
from resource_monitor import ResourceMonitor

# Custom thresholds
custom_thresholds = {
    "cpu_percent": 70.0,
    "memory_percent": 80.0,
    "disk_percent": 85.0,
    "disk_free_gb": 5.0
}

monitor = ResourceMonitor(alert_thresholds=custom_thresholds)
metrics = monitor.collect_metrics()
alerts = monitor.check_alerts(metrics)
```

### Continuous Monitoring Setup

#### Systemd Service (Linux)

Create `/etc/systemd/system/mcp-resource-monitor.service`:

```ini
[Unit]
Description=MCP Knowledge Server Resource Monitor
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-knowledge-server
ExecStart=/opt/mcp-knowledge-server/.venv/bin/python monitoring/resource_monitor.py --interval 60 --alert
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-resource-monitor
sudo systemctl start mcp-resource-monitor
```

#### Cron-based Monitoring

```bash
# Every minute, log metrics
* * * * * cd /path/to/mcp-knowledge-server && .venv/bin/python monitoring/resource_monitor.py --interval 0 --json >> /var/log/mcp-resources.log 2>&1

# Every 5 minutes, check alerts
*/5 * * * * cd /path/to/mcp-knowledge-server && .venv/bin/python monitoring/resource_monitor.py --interval 0 --alert
```

---

## Service Monitoring with Auto-Restart

### Overview

The service monitor (`service_monitor.sh`) ensures the MCP server process is running and can automatically restart it with configurable cooldown periods.

### Usage

```bash
# Basic monitoring check
./monitoring/service_monitor.sh

# Enable auto-restart
./monitoring/service_monitor.sh --auto-restart

# Custom cooldown period (seconds)
./monitoring/service_monitor.sh --auto-restart --cooldown 600
```

### Features

1. **Process Monitoring**: Checks if `mcp_server.py` is running
2. **Dependency Validation**: Ensures Neo4j is running before restart
3. **Cooldown Management**: Prevents restart loops
4. **Resource Reporting**: Shows CPU and memory usage
5. **Log Rotation**: Automatically rotates large log files

### Auto-Restart Configuration

**Cooldown Period**: Minimum time between restart attempts (default: 300 seconds)

**Prerequisites for Restart**:

- Neo4j must be running
- Virtual environment must exist
- Cooldown period must have elapsed

### Deployment Patterns

#### Cron-based Monitoring

```bash
# Check every 5 minutes, auto-restart if down
*/5 * * * * /path/to/mcp-knowledge-server/monitoring/service_monitor.sh --auto-restart >> /var/log/mcp-service.log 2>&1
```

#### Systemd Service with Watchdog

Create `/etc/systemd/system/mcp-server.service`:

```ini
[Unit]
Description=MCP Knowledge Server
After=docker.service neo4j.service
Requires=docker.service

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-knowledge-server
ExecStart=/opt/mcp-knowledge-server/.venv/bin/python mcp_server.py
Restart=on-failure
RestartSec=30
StartLimitInterval=300
StartLimitBurst=5

# Watchdog
WatchdogSec=60
NotifyAccess=main

[Install]
WantedBy=multi-user.target
```

### State Management

The service monitor maintains state in `.service_monitor_state`:

```bash
# View last restart time
cat monitoring/.service_monitor_state

# Manually reset cooldown
rm monitoring/.service_monitor_state
```

### Log Files

**Default Location**: `/var/log/mcp-service-monitor.log`
**Fallback**: `monitoring/service_monitor.log`

**Log Rotation**: Automatic when file exceeds 10MB

**Log Format**:

```
[2025-10-07 12:00:00] ========== Service Monitor Check ==========
[2025-10-07 12:00:00] ✅ MCP server is running (PID: 12345)
[2025-10-07 12:00:00]    CPU/Memory: 2.5 1.8
[2025-10-07 12:00:00] ✅ Neo4j is running
[2025-10-07 12:00:00] ✅ Neo4j port 7687 is accessible
[2025-10-07 12:00:00] 📊 Data directory size: 245M
[2025-10-07 12:00:00] ========== Check Complete ==========
```

---

## Prometheus Integration

### Overview

Export MCP server metrics to Prometheus for centralized monitoring and alerting.

### Prometheus Exporter Setup

#### Using Resource Monitor

```bash
# Export metrics to file
python monitoring/resource_monitor.py --interval 0 --prometheus > /var/lib/prometheus/node_exporter/mcp_metrics.prom
```

#### Continuous Export Script

Create `monitoring/prometheus_exporter.sh`:

```bash
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
METRICS_FILE="/var/lib/prometheus/node_exporter/mcp_metrics.prom"

while true; do
    cd "$PROJECT_DIR"
    .venv/bin/python monitoring/resource_monitor.py --interval 0 --prometheus > "$METRICS_FILE.tmp"
    mv "$METRICS_FILE.tmp" "$METRICS_FILE"
    sleep 60
done
```

Make executable and run:

```bash
chmod +x monitoring/prometheus_exporter.sh
nohup ./monitoring/prometheus_exporter.sh &
```

### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
global:
  scrape_interval: 60s
  evaluation_interval: 60s

scrape_configs:
  - job_name: 'mcp-knowledge-server'
    static_configs:
      - targets: ['localhost:9090']
    file_sd_configs:
      - files:
          - '/var/lib/prometheus/node_exporter/mcp_metrics.prom'
        refresh_interval: 60s
```

### Custom Prometheus Exporter (HTTP Server)

For production environments, create a dedicated HTTP exporter:

```python
#!/usr/bin/env python3
"""
Prometheus HTTP exporter for MCP Knowledge Server
"""

import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from monitoring.resource_monitor import ResourceMonitor

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            monitor = ResourceMonitor()
            metrics = monitor.collect_metrics()
            output = monitor.generate_prometheus_metrics(metrics)

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(output.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=9100)
    args = parser.parse_args()

    server = HTTPServer(('0.0.0.0', args.port), MetricsHandler)
    print(f"Prometheus exporter running on port {args.port}")
    server.serve_forever()

if __name__ == '__main__':
    main()
```

Update Prometheus config:

```yaml
scrape_configs:
  - job_name: 'mcp-knowledge-server'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 30s
```

---

## Grafana Dashboard Setup

### Overview

Visualize MCP server metrics with pre-built Grafana dashboards.

### Dashboard Installation

1. **Import Dashboard**: Grafana UI → Create → Import
2. **Paste JSON**: Use dashboard JSON below
3. **Select Data Source**: Choose your Prometheus instance

### MCP Knowledge Server Dashboard JSON

```json
{
  "dashboard": {
    "title": "MCP Knowledge Server Monitoring",
    "tags": ["mcp", "knowledge-server"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Server Status",
        "type": "stat",
        "targets": [
          {
            "expr": "mcp_process_running",
            "legendFormat": "Server Running"
          }
        ],
        "gridPos": { "h": 4, "w": 4, "x": 0, "y": 0 },
        "fieldConfig": {
          "defaults": {
            "mappings": [
              { "value": 1, "text": "Running", "color": "green" },
              { "value": 0, "text": "Down", "color": "red" }
            ]
          }
        }
      },
      {
        "id": 2,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_cpu_percent",
            "legendFormat": "System CPU"
          },
          {
            "expr": "mcp_process_cpu_percent",
            "legendFormat": "Process CPU"
          }
        ],
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 4 },
        "yaxes": [{ "label": "Percent", "min": 0, "max": 100 }]
      },
      {
        "id": 3,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_memory_percent",
            "legendFormat": "System Memory"
          },
          {
            "expr": "mcp_process_memory_mb",
            "legendFormat": "Process Memory (MB)"
          }
        ],
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 4 }
      },
      {
        "id": 4,
        "title": "Disk Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "mcp_disk_percent",
            "legendFormat": "Disk %"
          }
        ],
        "gridPos": { "h": 6, "w": 6, "x": 0, "y": 12 },
        "fieldConfig": {
          "defaults": {
            "max": 100,
            "thresholds": {
              "steps": [
                { "value": 0, "color": "green" },
                { "value": 80, "color": "yellow" },
                { "value": 90, "color": "red" }
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Free Disk Space",
        "type": "stat",
        "targets": [
          {
            "expr": "mcp_disk_free_gb",
            "legendFormat": "Free GB"
          }
        ],
        "gridPos": { "h": 6, "w": 6, "x": 6, "y": 12 },
        "fieldConfig": {
          "defaults": {
            "unit": "decgbytes",
            "thresholds": {
              "steps": [
                { "value": 0, "color": "red" },
                { "value": 5, "color": "yellow" },
                { "value": 20, "color": "green" }
              ]
            }
          }
        }
      },
      {
        "id": 6,
        "title": "Event Store Metrics",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_event_store_events",
            "legendFormat": "Total Events"
          },
          {
            "expr": "mcp_outbox_pending",
            "legendFormat": "Outbox Pending"
          }
        ],
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 18 }
      },
      {
        "id": 7,
        "title": "Database Sizes",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_database_size_mb{database=\"event_store\"}",
            "legendFormat": "Event Store (MB)"
          },
          {
            "expr": "mcp_database_size_mb{database=\"chromadb\"}",
            "legendFormat": "ChromaDB (MB)"
          }
        ],
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 18 },
        "yaxes": [{ "label": "Size (MB)" }]
      }
    ],
    "refresh": "30s",
    "time": { "from": "now-1h", "to": "now" }
  }
}
```

### Key Visualizations

1. **Server Status**: Real-time process status indicator
2. **CPU Usage**: System and process CPU over time
3. **Memory Usage**: RAM consumption trends
4. **Disk Usage**: Storage utilization gauge
5. **Event Store**: Event and outbox growth
6. **Database Sizes**: Storage growth tracking

### Alert Panels

Add alert panels for critical thresholds:

```json
{
  "id": 10,
  "title": "Critical Alerts",
  "type": "alertlist",
  "gridPos": { "h": 8, "w": 12, "x": 0, "y": 26 },
  "options": {
    "showOptions": "current",
    "stateFilter": {
      "firing": true,
      "pending": true
    }
  }
}
```

---

## Alert Thresholds and Notifications

### Alert Definitions

#### Critical Alerts (P1)

**Server Down**:

- **Metric**: `mcp_process_running == 0`
- **Threshold**: Process not running for > 2 minutes
- **Action**: Auto-restart (if enabled), page on-call

**Database Unavailable**:

- **Metric**: Health check Neo4j status
- **Threshold**: Connection failed
- **Action**: Page on-call, check Neo4j

**Disk Full**:

- **Metric**: `mcp_disk_free_gb < 1`
- **Threshold**: < 1GB free
- **Action**: Emergency cleanup, expand volume

**Data Corruption**:

- **Metric**: SQLite integrity check
- **Threshold**: integrity != "ok"
- **Action**: Page on-call, restore from backup

#### Warning Alerts (P2)

**High CPU**:

- **Metric**: `mcp_cpu_percent > 80`
- **Threshold**: > 80% for 5 minutes
- **Action**: Investigate, consider scaling

**High Memory**:

- **Metric**: `mcp_memory_percent > 85`
- **Threshold**: > 85% for 5 minutes
- **Action**: Check for leaks, restart if needed

**Disk Nearly Full**:

- **Metric**: `mcp_disk_percent > 90`
- **Threshold**: > 90% usage
- **Action**: Plan cleanup, monitor growth

**High Outbox Pending**:

- **Metric**: `mcp_outbox_pending > 100`
- **Threshold**: > 100 items
- **Action**: Check event processing, investigate failures

#### Informational Alerts (P3)

**Gradual Performance Degradation**:

- **Metric**: Response time trends
- **Threshold**: 20% increase over 24h
- **Action**: Review logs, plan optimization

**Database Growth**:

- **Metric**: `rate(mcp_database_size_mb[1d])`
- **Threshold**: Unusual growth rate
- **Action**: Review data retention policies

### Prometheus Alert Rules

Create `mcp_alerts.yml`:

```yaml
groups:
  - name: mcp_critical
    interval: 30s
    rules:
      - alert: MCPServerDown
        expr: mcp_process_running == 0
        for: 2m
        labels:
          severity: critical
          component: mcp-server
        annotations:
          summary: 'MCP Server is down'
          description: 'MCP server process has been down for 2 minutes'

      - alert: DiskSpaceCritical
        expr: mcp_disk_free_gb < 1
        for: 1m
        labels:
          severity: critical
          component: storage
        annotations:
          summary: 'Critical: Less than 1GB disk space'
          description: 'Free disk space: {{ $value }}GB'

      - alert: HighOutboxPending
        expr: mcp_outbox_pending > 100
        for: 10m
        labels:
          severity: warning
          component: event-processing
        annotations:
          summary: 'High number of pending outbox items'
          description: '{{ $value }} items pending in outbox'

  - name: mcp_performance
    interval: 1m
    rules:
      - alert: HighCPUUsage
        expr: mcp_cpu_percent > 80
        for: 5m
        labels:
          severity: warning
          component: performance
        annotations:
          summary: 'High CPU usage detected'
          description: 'CPU usage at {{ $value }}%'

      - alert: HighMemoryUsage
        expr: mcp_memory_percent > 85
        for: 5m
        labels:
          severity: warning
          component: performance
        annotations:
          summary: 'High memory usage detected'
          description: 'Memory usage at {{ $value }}%'
```

### Alertmanager Configuration

Configure `alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'component']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/alerts'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your-pagerduty-key>'
        description: '{{ .GroupLabels.alertname }}: {{ .Annotations.summary }}'

  - name: 'slack'
    slack_configs:
      - api_url: '<your-slack-webhook>'
        channel: '#mcp-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'component']
```

### Email Notifications

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops-team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: '<app-password>'
        headers:
          Subject: 'MCP Alert: {{ .GroupLabels.alertname }}'
```

---

## Metrics Reference

### Complete Metrics Catalog

#### System Metrics

| Metric Name               | Type  | Description             | Unit            |
| ------------------------- | ----- | ----------------------- | --------------- |
| `mcp_cpu_percent`         | Gauge | System CPU usage        | Percent (0-100) |
| `mcp_cpu_count`           | Gauge | Number of CPU cores     | Count           |
| `mcp_cpu_load_1min`       | Gauge | 1-minute load average   | Load            |
| `mcp_cpu_load_5min`       | Gauge | 5-minute load average   | Load            |
| `mcp_cpu_load_15min`      | Gauge | 15-minute load average  | Load            |
| `mcp_memory_percent`      | Gauge | Memory usage percentage | Percent (0-100) |
| `mcp_memory_total_gb`     | Gauge | Total system memory     | Gigabytes       |
| `mcp_memory_available_gb` | Gauge | Available memory        | Gigabytes       |
| `mcp_memory_used_gb`      | Gauge | Used memory             | Gigabytes       |
| `mcp_swap_percent`        | Gauge | Swap usage percentage   | Percent (0-100) |
| `mcp_disk_percent`        | Gauge | Disk usage percentage   | Percent (0-100) |
| `mcp_disk_free_gb`        | Gauge | Free disk space         | Gigabytes       |
| `mcp_disk_total_gb`       | Gauge | Total disk space        | Gigabytes       |
| `mcp_disk_used_gb`        | Gauge | Used disk space         | Gigabytes       |

#### Process Metrics

| Metric Name                  | Type  | Description                               | Unit      |
| ---------------------------- | ----- | ----------------------------------------- | --------- |
| `mcp_process_running`        | Gauge | Server process status (1=running, 0=down) | Boolean   |
| `mcp_process_cpu_percent`    | Gauge | Process CPU usage                         | Percent   |
| `mcp_process_memory_mb`      | Gauge | Process memory usage                      | Megabytes |
| `mcp_process_memory_percent` | Gauge | Process memory percentage                 | Percent   |
| `mcp_process_threads`        | Gauge | Number of threads                         | Count     |
| `mcp_process_open_files`     | Gauge | Open file descriptors                     | Count     |
| `mcp_process_connections`    | Gauge | Active network connections                | Count     |

#### Database Metrics

| Metric Name                                    | Type    | Description             | Unit         |
| ---------------------------------------------- | ------- | ----------------------- | ------------ |
| `mcp_event_store_events`                       | Counter | Total events in store   | Count        |
| `mcp_outbox_pending`                           | Gauge   | Pending outbox items    | Count        |
| `mcp_outbox_failed`                            | Gauge   | Failed outbox items     | Count        |
| `mcp_database_size_mb{database="event_store"}` | Gauge   | Event store size        | Megabytes    |
| `mcp_database_size_mb{database="chromadb"}`    | Gauge   | Vector DB size          | Megabytes    |
| `mcp_neo4j_latency_ms`                         | Gauge   | Neo4j query latency     | Milliseconds |
| `mcp_neo4j_concept_count`                      | Gauge   | Total concepts in graph | Count        |

#### Health Check Metrics

| Metric Name           | Type  | Description           | Values                             |
| --------------------- | ----- | --------------------- | ---------------------------------- |
| `mcp_health_overall`  | Gauge | Overall health status | 0=unhealthy, 1=degraded, 2=healthy |
| `mcp_health_neo4j`    | Gauge | Neo4j health          | 0=unhealthy, 1=degraded, 2=healthy |
| `mcp_health_sqlite`   | Gauge | SQLite health         | 0=unhealthy, 1=degraded, 2=healthy |
| `mcp_health_chromadb` | Gauge | ChromaDB health       | 0=unhealthy, 1=degraded, 2=healthy |

### Metric Interpretation

#### CPU Metrics

- **Normal**: < 50% average
- **Elevated**: 50-80% sustained
- **High**: > 80% for > 5 minutes
- **Critical**: > 95% sustained

**Investigation Steps for High CPU**:

1. Check process CPU: `top` or `htop`
2. Review recent operations (large imports, complex queries)
3. Check for runaway processes
4. Consider scaling if load is legitimate

#### Memory Metrics

- **Normal**: < 70% usage
- **Elevated**: 70-85% usage
- **High**: > 85% usage
- **Critical**: > 95% or swapping

**Investigation Steps for High Memory**:

1. Check for memory leaks: monitor over time
2. Review process memory growth
3. Analyze database cache sizes
4. Check for large in-memory operations

#### Disk Metrics

- **Healthy**: > 20% free
- **Watch**: 10-20% free
- **Warning**: 5-10% free
- **Critical**: < 5% free

**Investigation Steps for Low Disk**:

1. Check database sizes: `du -sh data/*`
2. Review log file sizes
3. Check for temporary files
4. Plan data cleanup or expansion

#### Outbox Metrics

- **Normal**: < 10 pending
- **Elevated**: 10-50 pending
- **High**: 50-100 pending
- **Critical**: > 100 pending

**Investigation Steps for High Outbox**:

1. Check for event processing errors
2. Review failed items: `SELECT * FROM outbox WHERE status='failed'`
3. Verify downstream systems are available
4. Check network connectivity

---

## Log Aggregation and Analysis

### Log Types

1. **Application Logs**: MCP server operations
2. **Health Check Logs**: Health validation results
3. **Resource Monitor Logs**: Metrics over time
4. **Service Monitor Logs**: Process monitoring events
5. **Database Logs**: Neo4j, SQLite operations

### Centralized Logging with ELK Stack

#### Filebeat Configuration

Create `filebeat.yml`:

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/mcp-server.log
      - /var/log/mcp-service-monitor.log
      - /var/log/mcp-health.log
    fields:
      service: mcp-knowledge-server
      environment: production

  - type: log
    enabled: true
    paths:
      - /path/to/mcp-knowledge-server/monitoring/service_monitor.log
    fields:
      service: mcp-monitoring
      log_type: service_monitor

output.elasticsearch:
  hosts: ['localhost:9200']
  index: 'mcp-logs-%{+yyyy.MM.dd}'

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - decode_json_fields:
      fields: ['message']
      target: 'json'
      overwrite_keys: true
```

#### Logstash Configuration

Create `logstash-mcp.conf`:

```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "mcp-knowledge-server" {
    grok {
      match => {
        "message" => "\[%{TIMESTAMP_ISO8601:timestamp}\] %{LOGLEVEL:level} %{GREEDYDATA:log_message}"
      }
    }
    date {
      match => ["timestamp", "ISO8601"]
      target => "@timestamp"
    }
  }

  if [fields][log_type] == "service_monitor" {
    grok {
      match => {
        "message" => "\[%{TIMESTAMP_ISO8601:timestamp}\] %{GREEDYDATA:monitor_message}"
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "mcp-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Kibana Dashboards

**Create Index Pattern**: `mcp-logs-*`

**Saved Searches**:

1. **Error Logs**:

```
level: ERROR AND service: mcp-knowledge-server
```

2. **Server Restarts**:

```
monitor_message: "Attempting to start MCP server"
```

3. **Health Check Failures**:

```
overall_status: unhealthy
```

**Visualizations**:

1. **Error Rate Over Time** (Line chart)
2. **Log Level Distribution** (Pie chart)
3. **Top Error Messages** (Data table)
4. **Server Restart Events** (Timeline)

### Log Analysis Queries

#### Find Patterns Leading to Crashes

```bash
# Extract timestamps around server restart events
grep -B 50 "Attempting to start MCP server" /var/log/mcp-service-monitor.log | grep ERROR
```

#### Analyze Resource Exhaustion Events

```bash
# Find high memory warnings before failures
jq 'select(.system.memory.percent > 90)' /var/log/mcp-resources.log | jq .timestamp
```

#### Track Outbox Growth

```bash
# Plot outbox pending over time
jq -r '[.timestamp, .database.event_store.outbox_pending] | @csv' /var/log/mcp-resources.log > outbox_trend.csv
```

### Retention Policies

**Recommended Retention**:

- **Application Logs**: 30 days (compressed after 7 days)
- **Metrics Logs**: 90 days (1-minute resolution for 7 days, then 5-minute aggregates)
- **Health Checks**: 30 days
- **Service Monitor**: 60 days

**Implementation**:

```bash
# Daily log rotation with compression
/var/log/mcp-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 mcp mcp
}
```

---

## Performance Monitoring Best Practices

### 1. Establish Baselines

**Initial Baseline Collection** (first 2 weeks):

```bash
# Collect detailed metrics every 30 seconds
python monitoring/resource_monitor.py --interval 30 --json >> baseline_metrics.log &

# Run daily health checks
0 */6 * * * python monitoring/health_check.py --json >> baseline_health.log
```

**Analyze Baselines**:

```python
import json
import pandas as pd

# Load metrics
with open('baseline_metrics.log') as f:
    metrics = [json.loads(line) for line in f]

df = pd.json_normalize(metrics)

# Calculate percentiles
print("CPU Percentiles:")
print(df['system.cpu.percent'].describe(percentiles=[.5, .9, .95, .99]))

print("\nMemory Percentiles:")
print(df['system.memory.percent'].describe(percentiles=[.5, .9, .95, .99]))

# Identify peak usage times
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
peak_hours = df.groupby('hour')['system.cpu.percent'].mean().sort_values(ascending=False)
print("\nPeak Usage Hours:")
print(peak_hours.head(5))
```

### 2. Capacity Planning

**Track Growth Rates**:

```bash
# Weekly database growth
python monitoring/resource_monitor.py --interval 0 --json | \
  jq '{event_count: .database.event_store.event_count, event_store_mb: .database.event_store.size_mb, chromadb_mb: .database.chromadb.size_mb}'
```

**Forecast Capacity Needs**:

```python
# Calculate daily growth rate
import numpy as np
from scipy import stats

# Assuming 'sizes' is array of daily database sizes
sizes = [10.5, 10.8, 11.2, 11.5, 11.9, 12.3]
days = np.arange(len(sizes))

slope, intercept, r_value, p_value, std_err = stats.linregress(days, sizes)

# Forecast 90 days ahead
forecast_90d = intercept + slope * 90
print(f"Projected size in 90 days: {forecast_90d:.2f}MB")
```

### 3. Performance Testing

**Load Testing Script**:

```python
#!/usr/bin/env python3
"""
Simple load test for MCP server
"""

import asyncio
import time
from monitoring.resource_monitor import ResourceMonitor

async def simulate_load():
    """Simulate concurrent operations"""
    # Your load simulation logic
    await asyncio.sleep(0.1)

async def load_test(duration_seconds=300, concurrent_ops=10):
    """Run load test while monitoring"""
    monitor = ResourceMonitor()

    start_time = time.time()
    metrics_log = []

    # Start load
    tasks = [simulate_load() for _ in range(concurrent_ops)]

    while time.time() - start_time < duration_seconds:
        # Collect metrics every 10 seconds
        metrics = monitor.collect_metrics()
        metrics_log.append(metrics)

        await asyncio.sleep(10)

    # Cancel load
    for task in tasks:
        task.cancel()

    return metrics_log

# Run test
metrics = asyncio.run(load_test(duration_seconds=600, concurrent_ops=20))
```

### 4. Anomaly Detection

**Simple Anomaly Detection**:

```python
import numpy as np
from scipy import stats

def detect_anomalies(values, threshold=3):
    """
    Detect anomalies using z-score method

    Args:
        values: Array of metric values
        threshold: Z-score threshold (default: 3 standard deviations)

    Returns:
        Indices of anomalous values
    """
    z_scores = np.abs(stats.zscore(values))
    return np.where(z_scores > threshold)[0]

# Example usage
cpu_values = [45.2, 47.1, 46.8, 92.5, 48.2, 46.5]  # 92.5 is anomaly
anomalies = detect_anomalies(cpu_values)
print(f"Anomalies at indices: {anomalies}")
```

### 5. Continuous Optimization

**Monthly Performance Review Checklist**:

- [ ] Review average response times
- [ ] Analyze resource utilization trends
- [ ] Check for slow queries (> 1s)
- [ ] Review database growth vs. baseline
- [ ] Identify performance regressions
- [ ] Update capacity projections
- [ ] Adjust alert thresholds if needed
- [ ] Review and optimize slow operations

---

## Troubleshooting with Monitoring Data

### Common Issues and Diagnostic Workflows

#### Issue 1: Server Keeps Crashing

**Symptoms**:

- `mcp_process_running == 0` repeatedly
- Frequent restart attempts in service monitor logs

**Diagnostic Steps**:

1. Check recent logs before crash:

```bash
grep -B 100 "MCP server is NOT running" /var/log/mcp-service-monitor.log | tail -110
```

2. Review resource usage before crash:

```bash
# Get metrics from 10 minutes before last restart
last_restart=$(grep "Attempting to start" /var/log/mcp-service-monitor.log | tail -1 | awk '{print $1, $2}')
grep -B 20 "$last_restart" /var/log/mcp-resources.log
```

3. Check for memory exhaustion:

```bash
# Look for OOM (Out of Memory) killer events
dmesg | grep -i "out of memory"
sudo journalctl | grep -i "killed process.*mcp"
```

4. Verify dependencies:

```bash
# Check Neo4j status
docker ps | grep neo4j
# Test Neo4j connection
python monitoring/health_check.py --json | jq .checks.neo4j
```

**Common Causes**:

- Memory leak → Monitor `mcp_process_memory_mb` growth
- Neo4j unavailable → Check Neo4j logs
- Unhandled exceptions → Review application logs
- Resource exhaustion → Check `mcp_memory_percent`, `mcp_disk_free_gb`

#### Issue 2: High Outbox Pending Count

**Symptoms**:

- `mcp_outbox_pending > 100`
- Event processing appears stalled

**Diagnostic Steps**:

1. Check outbox status:

```bash
sqlite3 data/events.db "SELECT status, COUNT(*) FROM outbox GROUP BY status"
```

2. Examine failed items:

```bash
sqlite3 data/events.db "SELECT * FROM outbox WHERE status='failed' LIMIT 10"
```

3. Check event processing logs:

```bash
grep -i "outbox\|event" /var/log/mcp-server.log | tail -50
```

4. Verify downstream systems:

```bash
# Check Neo4j write capability
python monitoring/health_check.py --check-write --verbose
```

**Resolution**:

```python
# Manually retry failed items
import sqlite3

conn = sqlite3.connect('data/events.db')
cursor = conn.cursor()

# Reset failed items to pending
cursor.execute("UPDATE outbox SET status='pending', retry_count=0 WHERE status='failed'")
conn.commit()
print(f"Reset {cursor.rowcount} failed items")
conn.close()
```

#### Issue 3: Slow Query Performance

**Symptoms**:

- Increased latency in health checks
- High `mcp_neo4j_latency_ms` values

**Diagnostic Steps**:

1. Check Neo4j query performance:

```cypher
// In Neo4j browser
CALL dbms.listQueries() YIELD query, elapsedTimeMillis
WHERE elapsedTimeMillis > 1000
RETURN query, elapsedTimeMillis
ORDER BY elapsedTimeMillis DESC
```

2. Review recent slow queries:

```bash
# If query logging is enabled
grep "slow query" /var/log/neo4j/query.log
```

3. Analyze database size and indexes:

```cypher
// Check for missing indexes
CALL db.indexes() YIELD name, state, populationPercent
WHERE state <> 'ONLINE'
RETURN name, state, populationPercent
```

4. Check resource contention:

```bash
python monitoring/resource_monitor.py --interval 0 --json | jq '.system.cpu, .system.memory'
```

**Optimization**:

```cypher
// Add indexes for frequently queried properties
CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)

// Analyze query plans
EXPLAIN MATCH (c:Concept {name: 'example'}) RETURN c
```

#### Issue 4: Disk Space Exhaustion

**Symptoms**:

- `mcp_disk_free_gb < 2`
- `mcp_disk_percent > 90`

**Diagnostic Steps**:

1. Identify large files:

```bash
cd /path/to/mcp-knowledge-server
du -ah data/ | sort -rh | head -20
```

2. Check database sizes:

```bash
python monitoring/resource_monitor.py --interval 0 --json | jq .database
```

3. Review log file sizes:

```bash
du -sh /var/log/mcp-*.log
```

**Cleanup Actions**:

```bash
# 1. Compress old logs
find /var/log -name "mcp-*.log.*" -mtime +7 -exec gzip {} \;

# 2. Rotate service monitor logs
cd monitoring
if [ -f service_monitor.log ]; then
    mv service_monitor.log service_monitor.log.$(date +%Y%m%d)
    touch service_monitor.log
fi

# 3. Vacuum SQLite database
sqlite3 data/events.db "VACUUM"

# 4. Check for ChromaDB cleanup opportunities
# Review and archive old vector collections if applicable
```

### Diagnostic Dashboard

**Quick Status Check**:

```bash
#!/bin/bash
# quick_status.sh - Comprehensive status at a glance

echo "=== MCP Knowledge Server Status ==="
echo ""

# Health check
echo "HEALTH CHECK:"
python monitoring/health_check.py --json | jq -r '.overall_status'

# Process status
if pgrep -f "mcp_server.py" > /dev/null; then
    echo "Process: RUNNING (PID: $(pgrep -f 'mcp_server.py'))"
else
    echo "Process: DOWN"
fi

# Resource snapshot
echo ""
echo "RESOURCES:"
python monitoring/resource_monitor.py --interval 0 --json | jq '{
  cpu: .system.cpu.percent,
  memory: .system.memory.percent,
  disk: .system.disk.percent,
  disk_free_gb: .system.disk.free_gb
}'

# Database metrics
echo ""
echo "DATABASES:"
python monitoring/resource_monitor.py --interval 0 --json | jq '.database'

# Recent alerts
echo ""
echo "RECENT ALERTS:"
python monitoring/resource_monitor.py --interval 0 --alert 2>&1 | grep "🚨" || echo "No alerts"

echo ""
echo "=== End Status Check ==="
```

Make executable and run:

```bash
chmod +x quick_status.sh
./quick_status.sh
```

---

## Conclusion

This comprehensive monitoring guide provides the foundation for reliable, observable operation of the MCP Knowledge Server. Key takeaways:

1. **Use health checks** to validate component integrity
2. **Monitor resources** to prevent exhaustion and degradation
3. **Enable auto-restart** for automatic recovery from failures
4. **Export to Prometheus/Grafana** for centralized monitoring
5. **Configure alerts** for proactive issue detection
6. **Analyze logs** to understand system behavior
7. **Establish baselines** for capacity planning
8. **Follow diagnostic workflows** to resolve issues efficiently

### Next Steps

1. Deploy monitoring scripts to production environment
2. Configure Prometheus and Grafana dashboards
3. Set up alerting and notifications
4. Establish baseline metrics for your workload
5. Create runbooks for common issues
6. Schedule regular performance reviews

### Additional Resources

- **Health Check Script**: `/monitoring/health_check.py`
- **Resource Monitor**: `/monitoring/resource_monitor.py`
- **Service Monitor**: `/monitoring/service_monitor.sh`
- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **Neo4j Monitoring**: https://neo4j.com/docs/operations-manual/current/monitoring/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-07
**Maintained By**: MCP Knowledge Server Team
