from PyQt5.QtCore import QObject,QThread
from PyQt5.QtCore import  pyqtSignal
from config import loggers
import psutil
import netifaces
import json
from datetime import datetime

log=loggers['AGENTS']


class AlertCheck(QObject):
    alert_triggered = pyqtSignal(list)  # Signal to emit triggered alerts (stock and system)

    def __init__(self, db_tool, yahoo_tool, parent=None):
        super().__init__(parent)
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool
        self.running = False
        # Thresholds for proactive system alerts (customizable via preferences if desired)
        self.cpu_threshold = 90.0  # Alert if CPU usage > 90%
        self.memory_threshold = 90.0  # Alert if memory usage > 90%
        self.battery_threshold = 20.0  # Alert if battery < 20%
        self.disk_threshold = 90.0  # Alert if disk usage > 90%

    def get_system_sensors(self):
        """Fetch system metrics using psutil."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            return {
                "cpu": cpu_usage,
                "memory": memory.percent,
                "disk": disk.percent,
                "battery": battery.percent if battery else 100.0,  # Assume 100% if no battery
                "power_plugged": battery.power_plugged if battery else True
            }
        except Exception as e:
            return {"error": f"System monitoring failed: {str(e)}"}

    def get_network_status(self):
        """Check network connectivity using netifaces."""
        try:
            gateways = netifaces.gateways()
            return "connected" if 'default' in gateways and gateways['default'] else "disconnected"
        except Exception:
            return "unknown"

    def run(self):
        from core.personal_assistant import EXCHANGE_RATES  # Assuming EXCHANGE_RATES is defined here
        self.running = True
        while self.running:
            triggered = []  # Collect all alerts (stock + system)

            # 1. Stock Alerts (existing functionality)
            user_currency_result = self.db_tool._run("get_preference", key="currency", default="USD")
            user_currency = user_currency_result if user_currency_result in EXCHANGE_RATES else "USD"
            rate_to_usd = EXCHANGE_RATES[user_currency]
            alerts = json.loads(self.db_tool._run("get_alerts"))
            purchases = json.loads(self.db_tool._run("get_purchases_for_alerts"))

            # Stock price target alerts
            for ticker, target_price, alert_currency in alerts:
                data = json.loads(self.yahoo_tool._run(ticker))
                if "price" in data:
                    usd_price = data["price"]
                    alert_price_in_usd = target_price / EXCHANGE_RATES.get(alert_currency, 1.0)
                    if usd_price >= alert_price_in_usd:
                        converted_price = usd_price * EXCHANGE_RATES[user_currency]
                        triggered.append(
                            f"Alert: {data['company']} ({ticker}) is at {user_currency}{converted_price:.2f}, hit your target of {alert_currency}{target_price}"
                        )
                        self.db_tool._run("log_notification",
                                        message=f"Alert triggered for {ticker} at {user_currency}{converted_price:.2f}")

            # Stock profit reminders
            for ticker, purchase_price, quantity, purchase_currency in purchases:
                data = json.loads(self.yahoo_tool._run(ticker))
                if "price" in data:
                    usd_price = data["price"]
                    purchase_price_usd = purchase_price / EXCHANGE_RATES.get(purchase_currency, 1.0)
                    target_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_target_profit", default=0))
                    min_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_min_profit", default=0))
                    profit_usd = (usd_price - purchase_price_usd) * quantity
                    target_price_usd = purchase_price_usd + target_profit
                    if usd_price >= target_price_usd and profit_usd >= min_profit:
                        converted_price = usd_price * EXCHANGE_RATES[user_currency]
                        converted_profit = profit_usd * EXCHANGE_RATES[user_currency]
                        triggered.append(
                            f"Reminder: {data['company']} ({ticker}) bought at {purchase_currency}{purchase_price} is now {user_currency}{converted_price:.2f}. Selling yields profit of {user_currency}{converted_profit:.2f} (≥ {user_currency}{min_profit})."
                        )
                        self.db_tool._run("log_notification",
                                        message=f"Profit reminder for {ticker}: {user_currency}{converted_profit:.2f}")

            # 2. System Monitoring and Proactive Updates
            sensors = self.get_system_sensors()
            network_status = self.get_network_status()

            # CPU usage alert
            if "cpu" in sensors and sensors["cpu"] > self.cpu_threshold:
                triggered.append(f"Warning: CPU usage at {sensors['cpu']:.1f}%, exceeding {self.cpu_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High CPU usage detected: {sensors['cpu']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Memory usage alert
            if "memory" in sensors and sensors["memory"] > self.memory_threshold:
                triggered.append(f"Warning: Memory usage at {sensors['memory']:.1f}%, exceeding {self.memory_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High memory usage detected: {sensors['memory']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Disk usage alert
            if "disk" in sensors and sensors["disk"] > self.disk_threshold:
                triggered.append(f"Warning: Disk usage at {sensors['disk']:.1f}%, exceeding {self.disk_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"High disk usage detected: {sensors['disk']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Battery level alert (if not plugged in)
            if "battery" in sensors and sensors["battery"] < self.battery_threshold and not sensors["power_plugged"]:
                triggered.append(f"Warning: Battery level at {sensors['battery']:.1f}%, below {self.battery_threshold}% threshold.")
                self.db_tool._run("log_notification",
                                message=f"Low battery detected: {sensors['battery']:.1f}% at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Network disconnection alert
            if network_status == "disconnected":
                triggered.append("Warning: Network connection lost.")
                self.db_tool._run("log_notification",
                                message=f"Network disconnection detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Emit all triggered alerts (stock + system)
            if triggered:
                self.alert_triggered.emit(triggered)

            # Sleep for 10 seconds (consistent with stock checks)
            QThread.msleep(10000)

    def stop(self):
        self.running = False
