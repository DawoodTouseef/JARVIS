# Copyright 2025 Dawood Thouseef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import asyncio
import threading
import gc
import time
import math
import secrets
import hashlib
import sqlite3
import json
import tempfile
import re
import ssl
import platform
import logging
import random
import yara
import bcrypt
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import psutil
import dns.resolver
import speedtest
import clamdpy
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CrewAI and LangChain imports (assuming these modules are installed)
from crewai import Agent, Task, Crew, Process, LLM
from langchain.tools import tool
from config import JARVIS_DIR


QUARANTINE_DIR = os.path.join(tempfile.gettempdir(), "quantum_vault")
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Database connection for incident logging
conn = sqlite3.connect(os.path.join(JARVIS_DIR, "incidents.db"))
c = conn.cursor()

# ClamAV socket
clam = clamdpy.ClamdNetworkSocket()
SYSTEM = platform.system()

# YARA rules for threat detection
yara_rules = yara.compile(source='''
rule QuantumThreats {
    strings:
        $malware = "trojan" nocase
        $exploit = "exploit" wide ascii
    condition:
        any of them
}
''')


# --------------------- [ TOOL FUNCTIONS & NEW FEATURES ] ---------------------

@tool("dark_web_monitor")
def dark_web_monitor():
    """
    Dark Web Monitor: Checks for leaked credentials on the dark web.
    (This is a placeholder; integrate with an API like HaveIBeenPwned in production.)
    """
    # For demonstration, randomly decide if credentials were found.
    if random.random() < 0.1:
        return {"status": "Leaked credentials detected!"}
    return {"status": "No leaks found."}


@tool("update_firewall_rules")
def update_firewall_rules(ip: str, action: str):
    """
    Automated Firewall Management: Dynamically block or unblock suspicious IPs.
    """
    try:
        if SYSTEM == 'Windows':
            # Insert Windows firewall rule code here
            return f"Windows Firewall: {action} {ip}"
        elif SYSTEM == 'Linux':
            # Use iptables commands or iptc library here
            return f"Linux Iptables: {action} {ip}"
        else:
            return f"Unsupported system: {SYSTEM}"
    except Exception as e:
        logging.error(f"Firewall update failed: {str(e)}")
        return "Firewall update failed"


@tool("deep_malware_scan")
def deep_malware_scan(file_path: str):
    """
    Deep Malware Scan: Uses a deep-learning model to analyze file behavior.
    (Placeholder: returns a dummy result.)
    """
    # Replace with actual deep-learning model inference
    return {"malware": False, "confidence": 0.98}


@tool("file_integrity_monitor")
def file_integrity_monitor():
    """
    File Integrity Monitoring: Checks critical files' SHA-256 hashes.
    """
    critical_files = {
        'Linux': ['/etc/passwd', '/etc/shadow', '/etc/sudoers'],
        'Darwin': ['/etc/master.passwd', '/etc/sudoers'],
        'Windows': [os.path.join(os.environ['WINDIR'], 'System32', 'config')]
    }
    results = {}
    for file in critical_files.get(SYSTEM, []):
        try:
            with open(file, 'rb') as f:
                data = f.read()
            hash_val = hashlib.sha256(data).hexdigest()
            results[file] = hash_val
        except Exception as e:
            results[file] = f"Access Denied: {str(e)}"
    return results


@tool("process_injection_detection")
def process_injection_detection():
    """
    Process Injection Detection: Scans running processes for suspicious injections.
    (Placeholder: returns dummy list.)
    """
    suspicious = []
    for proc in psutil.process_iter(['pid', 'name']):
        # Simple heuristic: if process name contains 'inject', flag it
        if "inject" in proc.info.get("name", "").lower():
            suspicious.append(proc.info)
    return suspicious


@tool("check_dns_poisoning")
def check_dns_poisoning():
    """
    DNS Poisoning Detection: Compares DNS resolutions against a trusted resolver.
    """
    resolver = dns.resolver.Resolver()
    try:
        trusted = ["8.8.8.8"]  # Example: Google's public DNS
        current = resolver.nameservers
        return {"trusted": trusted, "current": current, "poisoned": set(trusted) != set(current)}
    except Exception as e:
        return {"error": str(e)}


@tool("voice_alert")
def voice_alert(message: str):
    """
    Real-Time Voice Alert: Uses Text-to-Speech (TTS) to announce a security alert.
    (Placeholder: simply returns the message.)
    """
    # In production, integrate with a TTS engine like pyttsx3 or gTTS
    return f"Voice Alert: {message}"


@tool("async_network_speed")
async def async_network_speed():
    """
    Asynchronous Network Speed Test: Non-blocking speed test.
    """
    st = speedtest.Speedtest()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, st.download)
    await loop.run_in_executor(None, st.upload)
    return st.results.dict()


@tool("advanced_ssl_analysis")
def advanced_ssl_analysis(domain: str):
    """
    Advanced SSL Certificate Analysis: Checks for expiration and weak encryption.
    """
    cert = ssl.get_server_certificate((domain, 443))
    x509_cert = x509.load_pem_x509_certificate(cert.encode(), default_backend())
    return {
        'subject': x509_cert.subject.rfc4514_string(),
        'issuer': x509_cert.issuer.rfc4514_string(),
        'expires': x509_cert.not_valid_after.isoformat(),
        'signature_algorithm': x509_cert.signature_hash_algorithm.name
    }


@tool("monitor_drive_partitions")
def monitor_drive_partitions(threshold: float = 90.0):
    """
    Monitor all drive partitions and report disk usage.

    Returns:
        dict: A dictionary with each mount point's statistics and a list of alerts if usage exceeds the threshold.
    """
    import psutil
    results = {}
    alerts = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            results[part.mountpoint] = {
                "filesystem": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
            if usage.percent >= threshold:
                alerts.append(f"Partition {part.mountpoint} is {usage.percent}% full!")
        except Exception as e:
            results[part.mountpoint] = {"error": str(e)}
    return {"partitions": results, "alerts": alerts}


# --------------------- [ AI Security Agents & Crew ] ---------------------

llm = LLM(model="huggingface/deepseek-ai/DeepSeek-R1", api_key="YOUR_API_KEY")

system_monitor = Agent(
    role="System Security Analyst",
    goal="Monitor system integrity and detect anomalies",
    backstory="Expert in low-level system diagnostics and process analysis",
    tools=[process_injection_detection, file_integrity_monitor, deep_malware_scan],
    verbose=True,
    llm=llm
)

network_guardian = Agent(
    role="Network Security Expert",
    goal="Detect intrusions and ensure safe internet connectivity",
    backstory="Specializes in network protocol analysis and intrusion detection",
    tools=[async_network_speed, advanced_ssl_analysis, check_dns_poisoning, update_firewall_rules],
    verbose=True,
    llm=llm
)

dark_web_watcher = Agent(
    role="Dark Web Intelligence",
    goal="Monitor dark web for leaked credentials",
    backstory="Monitors external sources for leaked sensitive data",
    tools=[dark_web_monitor],
    verbose=True,
    llm=llm
)
drive_monitor_agent = Agent(
    role="Drive Monitor",
    goal="Monitor disk partitions and alert on high usage",
    backstory="Ensures no partition runs out of space or becomes a security risk due to heavy usage.",
    tools=[monitor_drive_partitions],
    verbose=True,
    llm=llm
)

# Create tasks for each agent
tasks = [
    Task(description="Monitor system processes and file integrity", agent=system_monitor, expected_output="System security report"),
    Task(description="Analyze network traffic and SSL certificates", agent=network_guardian, expected_output="Network security report"),
    Task(description="Monitor dark web for leaked credentials", agent=dark_web_watcher, expected_output="Dark web status"),
Task(description="Check disk partitions and report any alerts",agent=drive_monitor_agent,expected_output="Partition usage details and alerts if any partition is above threshold")
]



security_crew = Crew(agents=[system_monitor, network_guardian, dark_web_watcher,drive_monitor_agent],
                     tasks=tasks, process=Process.sequential)

# --------------------- [ Real-Time File Monitoring ] ---------------------

class QuantumGuardianHandler(FileSystemEventHandler):
    def on_created(self, event):
        self._process(event)

    def on_modified(self, event):
        self._process(event)

    def _process(self, event):
        if not event.is_directory:
            self._analyze_file(event.src_path)

    def _analyze_file(self, path):
        try:
            if yara_rules.match(path) or self._calculate_entropy(path) > 7.5:
                self._quarantine(path)
        except Exception as e:
            logging.error(f"File analysis failed: {e}")

    def _calculate_entropy(self, path):
        with open(path, "rb") as f:
            data = f.read()
        freq = {byte: data.count(byte) for byte in set(data)}
        entropy = -sum((count / len(data)) * math.log2(count / len(data)) for count in freq.values())
        return entropy

    def _quarantine(self, path):
        try:
            dest = os.path.join(QUARANTINE_DIR, f"{time.time()}_{os.path.basename(path)}")
            os.rename(path, dest)
            self._log_incident("QUARANTINE", dest)
        except Exception as e:
            logging.error(f"Quarantine failed: {e}")

    def _log_incident(self, inc_type, details):
        c.execute("INSERT INTO incidents (timestamp, type, details, action) VALUES (?, ?, ?, ?)",
                  (datetime.now().isoformat(), inc_type, details, "AUTO"))
        conn.commit()

# --------------------- [ Run Security System ] ---------------------

def start_security_monitoring():
    observer = Observer()
    observer.schedule(QuantumGuardianHandler(), path="/", recursive=True)
    observer.start()

    logging.info("🔐 Security system activated. Monitoring files and network...")
    try:
        while True:
            security_crew.kickoff()
            time.sleep(3600)  # Run tasks every hour
            gc.collect()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def get_threat_count():
    """Return the total number of incidents logged."""
    c.execute("SELECT COUNT(*) FROM incidents")
    return c.fetchone()[0]


