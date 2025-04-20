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

from PyQt5.QtCore import  QThread

from PyQt5.QtCore import   pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
)
import os


from datetime import datetime

from PyQt5.QtCore import Qt
import subprocess,platform


class SecurityIndicator(QWidget):
    """Circular security status indicator (Green=Secure, Red=Threat)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)
        self._status = False
        self.opacity = 1.0

    def set_status(self, active):
        """Change security status."""
        self._status = active
        self.update()

    def paintEvent(self, event):
        """Draw security indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 30, 30))
        painter.drawEllipse(0, 0, 90, 90)

        color = QColor(0, 255, 0) if self._status else QColor(255, 0, 0)
        painter.setBrush(color)
        painter.drawEllipse(20, 20, 50, 50)

class SecurityScanThread(QThread):
    """Thread to perform real security scanning."""
    scanCompleted = pyqtSignal(int)  # Emits number of detected threats

    def __init__(self, scan_type="quick"):
        super().__init__()
        self.scan_type = scan_type

    def run(self):
        """Runs system security scanning based on OS."""
        detected_threats = 0
        os_name = platform.system()

        if os_name == "Windows":
            detected_threats = self.scan_windows()
        elif os_name == "Linux":
            detected_threats = self.scan_linux()
        elif os_name == "Darwin":  # macOS
            detected_threats = self.scan_macos()

        self.scanCompleted.emit(detected_threats)

    def scan_windows(self):
        """Performs a security scan using Windows Defender."""
        try:
            scan_cmd = r'powershell -Command "Start-MpScan -ScanType QuickScan"'
            subprocess.run(scan_cmd, shell=True, check=True)

            result = subprocess.run(
                r'powershell -Command "Get-MpThreat | Measure-Object"',
                shell=True, capture_output=True, text=True
            )

            threats_found = int(result.stdout.strip().split()[-1]) if result.stdout.strip() else 0
            return threats_found

        except Exception as e:
            print(f"[Error] Windows Defender Scan Failed: {e}")
            return 0

    def scan_linux(self):
        """Performs a security scan using ClamAV on Linux."""
        try:
            if os.system("which clamscan > /dev/null 2>&1") != 0:
                print("[Error] ClamAV is not installed. Install it using 'sudo apt install clamav'")
                return 0

            os.system("freshclam")

            result = subprocess.run(
                "clamscan -r --bell -i /home",  # Modify path as needed
                shell=True, capture_output=True, text=True
            )

            threats = sum(1 for line in result.stdout.split("\n") if "FOUND" in line)
            return threats

        except Exception as e:
            print(f"[Error] ClamAV Scan Failed: {e}")
            return 0

    def scan_macos(self):
        """Performs a security scan using ClamAV on macOS."""
        return self.scan_linux()  # macOS also uses ClamAV


class SecurityDashboard(QWidget):
    """Security dashboard widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_threats = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        self.status_header = QLabel("🛡️ Quantum Security Shield")
        self.status_header.setStyleSheet("font-size: 18px; color: #00ffff; font-weight: bold;")

        stats_layout = QHBoxLayout()
        self.threat_count = QLabel("0 Threats Blocked")
        self.last_scan = QLabel("Last Scan: Never")
        stats_layout.addWidget(self.threat_count)
        stats_layout.addWidget(self.last_scan)

        self.security_indicator = QLabel("🟢 Secure")
        self.security_indicator.setAlignment(Qt.AlignCenter)
        self.security_indicator.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")

        control_layout = QHBoxLayout()
        self.quick_scan_btn = QPushButton("🚀 Quick Scan")
        self.full_scan_btn = QPushButton("🛑 Full Scan")
        control_layout.addWidget(self.quick_scan_btn)
        control_layout.addWidget(self.full_scan_btn)

        layout.addWidget(self.status_header)
        layout.addLayout(stats_layout)
        layout.addWidget(self.security_indicator, alignment=Qt.AlignCenter)
        layout.addLayout(control_layout)

        self.setLayout(layout)
        self.setStyleSheet("""
            background-color: rgba(40, 40, 40, 220);
            border-radius: 15px;
            border: 2px solid #505050;
        """)

        self.quick_scan_btn.clicked.connect(lambda: self.start_scan("quick"))
        self.full_scan_btn.clicked.connect(lambda: self.start_scan("full"))

    def start_scan(self, scan_type):
        """Starts the security scan."""
        self.security_indicator.setText("🟡 Scanning...")
        self.security_indicator.setStyleSheet("font-size: 16px; color: orange; font-weight: bold;")

        self.scan_thread = SecurityScanThread(scan_type)
        self.scan_thread.scanCompleted.connect(self.update_scan_results)
        self.scan_thread.start()

    def update_scan_results(self, detected_threats):
        """Updates UI with scan results."""
        self.total_threats += detected_threats
        self.threat_count.setText(f"{self.total_threats} Threats Blocked")
        self.last_scan.setText(f"Last Scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if detected_threats > 0:
            self.security_indicator.setText("🔴 Threats Detected!")
            self.security_indicator.setStyleSheet("font-size: 16px; color: red; font-weight: bold;")
        else:
            self.security_indicator.setText("🟢 Secure")
            self.security_indicator.setStyleSheet("font-size: 16px; color: green; font-weight: bold;")

    def closeEvent(self, a0):
        self.scan_thread.quit()
        self.scan_thread.wait()

        a0.accept()