import json

import psutil



# Sensor Functions
def get_system_sensors():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        battery = psutil.sensors_battery()
        sensor_data = {
            "CPU Usage": f"{cpu_usage}%",
            "Memory Usage": f"{memory.percent}% ({memory.used / (1024**3):.2f}/{memory.total / (1024**3):.2f} GB)",
            "Disk Usage": f"{disk.percent}% ({disk.used / (1024**3):.2f}/{disk.total / (1024**3):.2f} GB)",
            "Battery": f"{battery.percent}% (Plugged in: {battery.power_plugged})" if battery else "No battery detected"
        }
        return sensor_data
    except Exception as e:
        return {"Error": f"Failed to retrieve sensor data: {e}"}

def create_sensor_tools():
    from langchain.tools import Tool
    return [
        Tool(
            name="get_system_sensors",
            func=lambda _: json.dumps(get_system_sensors()),
            description="Retrieve current system sensor data (CPU, memory, disk, battery)"
        )
    ]