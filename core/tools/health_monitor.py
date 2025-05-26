import psutil
from langchain.tools import Tool
from datetime import datetime

class SystemMonitorAgent:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {
            'cpu': 85,
            'memory': 80,
            'disk': 90
        }

    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self):
        mem = psutil.virtual_memory()
        return mem.percent, mem.used // (1024 ** 2), mem.total // (1024 ** 2)

    def get_disk_usage(self):
        disk = psutil.disk_usage('/')
        return disk.percent, disk.used // (1024 ** 3), disk.total // (1024 ** 3)

    def get_network_stats(self):
        net = psutil.net_io_counters()
        return net.bytes_sent, net.bytes_recv

    def check_alerts(self, cpu, memory, disk):
        alerts = []
        if cpu > self.thresholds['cpu']:
            alerts.append(f"⚠️ High CPU usage: {cpu}%")
        if memory > self.thresholds['memory']:
            alerts.append(f"⚠️ High Memory usage: {memory}%")
        if disk > self.thresholds['disk']:
            alerts.append(f"⚠️ High Disk usage: {disk}%")
        return alerts

    def report(self):
        cpu = self.get_cpu_usage()
        mem_percent, mem_used, mem_total = self.get_memory_usage()
        disk_percent, disk_used, disk_total = self.get_disk_usage()
        sent, recv = self.get_network_stats()

        alerts = self.check_alerts(cpu, mem_percent, disk_percent)
        return {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "cpu": f"{cpu}%",
            "memory": f"{mem_percent}% ({mem_used}MB / {mem_total}MB)",
            "disk": f"{disk_percent}% ({disk_used}GB / {disk_total}GB)",
            "network": {
                "sent_MB": sent // (1024 ** 2),
                "recv_MB": recv // (1024 ** 2)
            },
            "alerts": alerts
        }

def system_health_check_tool() -> Tool:
    agent = SystemMonitorAgent()

    def _run():
        status = agent.report()
        # Flatten status into a printable string
        summary = f"""🖥️ System Health Report @ {status['timestamp']}:
- CPU Usage: {status['cpu']}
- Memory Usage: {status['memory']}
- Disk Usage: {status['disk']}
- Network Sent: {status['network']['sent_MB']} MB
- Network Received: {status['network']['recv_MB']} MB
"""
        if status['alerts']:
            summary += "\n⚠️ Alerts:\n" + "\n".join(status['alerts'])
        else:
            summary += "\n✅ All systems normal."
        return summary

    return Tool(
        name="SystemHealthMonitor",
        func=_run,
        description="Use this tool to check the current system health (CPU, memory, disk, and network usage)."
    )

if __name__=="__main__":
    c=system_health_check_tool()
    print(c.func())