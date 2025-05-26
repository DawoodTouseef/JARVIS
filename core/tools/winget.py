import json

import winreg
import requests
import ctypes
import shutil
import platform
from functools import lru_cache

# WingetAPI Class
class WingetAPI:
    def __init__(self):
        self.winget_repo = "https://api.winget.run/v2/packages"
        self.registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

    @lru_cache(maxsize=1)
    def list_installed_software(self):
        installed_software = set()
        for hive, path in self.registry_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, i)) as subkey:
                                name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                installed_software.add(name)
                        except (FileNotFoundError, OSError):
                            continue
            except Exception:
                continue
        return sorted(installed_software)

    def search_software(self, query):
        try:
            response = requests.get(f"{self.winget_repo}/{query}", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def execute_winget_command(self, command):
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {command}", None, 1)
            return f"Executing: {command}"
        except Exception as e:
            return f"Error executing command: {e}"

    def install_software(self, software_id):
        return self.execute_winget_command(f"winget install --id {software_id} -e --accept-package-agreements --accept-source-agreements")

    def uninstall_software(self, software_id):
        return self.execute_winget_command(f"winget uninstall --id {software_id} -e")

    def export_installed_software(self, filename="installed_software.json"):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.list_installed_software(), f, indent=4)
            return f"Software list exported to {filename}"
        except Exception as e:
            return f"Error exporting software list: {e}"

    def check_software_installed(self, software_name):
        return software_name in self.list_installed_software()

    @staticmethod
    def get_system_info():
        disk_usage = shutil.disk_usage("/")
        return {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Architecture": platform.architecture()[0],
            "Processor": platform.processor(),
            "Total Disk Space (GB)": round(disk_usage.total / (1024**3), 2),
            "Free Disk Space (GB)": round(disk_usage.free / (1024**3), 2)
        }

    def update_winget(self):
        return self.execute_winget_command("winget upgrade --all --accept-package-agreements --accept-source-agreements")

# Winget Tools
def create_winget_tools():
    from langchain.tools import Tool
    winget_api = WingetAPI()
    return [
        Tool(
            name="list_installed_software",
            func=lambda _: "\n".join(winget_api.list_installed_software()),
            description="List all installed software on the system"
        ),
        Tool(
            name="search_software",
            func=lambda query: json.dumps(winget_api.search_software(query)),
            description="Search for software in the Winget repository"
        ),
        Tool(
            name="install_software",
            func=winget_api.install_software,
            description="Install software using Winget by ID (e.g., 'Google.Chrome')"
        ),
        Tool(
            name="uninstall_software",
            func=winget_api.uninstall_software,
            description="Uninstall software using Winget by ID"
        ),
        Tool(
            name="check_software_installed",
            func=winget_api.check_software_installed,
            description="Check if a specific software is installed"
        ),
        Tool(
            name="export_installed_software",
            func=lambda _: winget_api.export_installed_software(),
            description="Export the list of installed software to a JSON file"
        ),
        Tool(
            name="get_system_info",
            func=lambda _: json.dumps(winget_api.get_system_info()),
            description="Retrieve system information"
        ),
        Tool(
            name="update_all_software",
            func=lambda _: winget_api.update_winget(),
            description="Update all installed software via Winget"
        )
    ]
