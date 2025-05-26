from PyQt5.QtCore import QObject, QThread, pyqtSignal
from config import loggers, PLUGIN_DIR
import psutil, netifaces, json
from datetime import datetime
import os
import importlib.util
from jarvis_integration.alert_plugins.base import BaseAlertPlugin
from config import JARVIS_DIR

log = loggers['AGENTS']

class AlertCheck(QObject):
    alert_triggered = pyqtSignal(list)  # Signal to emit alerts (both system + stock)

    def __init__(self, db_tool, yahoo_tool, parent=None):
        super().__init__(parent)
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool
        self.running = False
        self.plugins = []
        self.cpu_threshold = 90.0
        self.memory_threshold = 90.0
        self.battery_threshold = 20.0
        self.disk_threshold = 90.0
        self.load_plugins()

    def get_system_sensors(self):
        try:
            battery = psutil.sensors_battery()
            return {
                "cpu": psutil.cpu_percent(interval=1),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent,
                "battery": battery.percent if battery else 100,
                "power_plugged": battery.power_plugged if battery else True
            }
        except Exception as e:
            log.error(f"Sensor error: {e}")
            return {}

    def get_network_status(self):
        try:
            gateways = netifaces.gateways()
            return "connected" if 'default' in gateways and gateways['default'] else "disconnected"
        except Exception:
            return "unknown"

    def check_stock_alerts(self, triggered):
        from core.agents.personal_assistant import EXCHANGE_RATES
        currency = self.db_tool._run("get_preference", key="currency", default="USD")
        currency = currency if currency in EXCHANGE_RATES else "USD"
        rate_to_usd = EXCHANGE_RATES[currency]

        alerts = json.loads(self.db_tool._run("get_alerts"))
        purchases = json.loads(self.db_tool._run("get_purchases_for_alerts"))

        for ticker, target_price, alert_currency in alerts:
            data = json.loads(self.yahoo_tool._run(ticker))
            if "price" in data:
                usd_price = data["price"]
                alert_price_usd = target_price / EXCHANGE_RATES.get(alert_currency, 1)
                if usd_price >= alert_price_usd:
                    converted = usd_price * EXCHANGE_RATES[currency]
                    triggered.append(
                        f"📈 {data['company']} ({ticker}) hit {currency}{converted:.2f} (target: {alert_currency}{target_price})"
                    )
                    self.db_tool._run("log_notification", message=f"Stock alert for {ticker} at {currency}{converted:.2f}")

        for ticker, buy_price, qty, buy_currency in purchases:
            data = json.loads(self.yahoo_tool._run(ticker))
            if "price" in data:
                usd_price = data["price"]
                buy_price_usd = buy_price / EXCHANGE_RATES.get(buy_currency, 1)
                target_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_target_profit", default=0))
                min_profit = float(self.db_tool._run("get_preference", key=f"{ticker}_min_profit", default=0))

                profit = (usd_price - buy_price_usd) * qty
                if usd_price >= buy_price_usd + target_profit and profit >= min_profit:
                    converted_profit = profit * EXCHANGE_RATES[currency]
                    triggered.append(
                        f"💰 {data['company']} ({ticker}) profit: {currency}{converted_profit:.2f} (qty: {qty})"
                    )
                    self.db_tool._run("log_notification", message=f"Profit alert for {ticker}: {currency}{converted_profit:.2f}")

    def check_system_alerts(self, triggered):
        sensors = self.get_system_sensors()
        network_status = self.get_network_status()

        if sensors.get("cpu", 0) > self.cpu_threshold:
            triggered.append(f"🔥 CPU usage {sensors['cpu']:.1f}% exceeds {self.cpu_threshold}%")
        if sensors.get("memory", 0) > self.memory_threshold:
            triggered.append(f"🧠 Memory usage {sensors['memory']:.1f}% exceeds {self.memory_threshold}%")
        if sensors.get("disk", 0) > self.disk_threshold:
            triggered.append(f"💾 Disk usage {sensors['disk']:.1f}% exceeds {self.disk_threshold}%")
        if sensors.get("battery", 100) < self.battery_threshold and not sensors.get("power_plugged", True):
            triggered.append(f"🔋 Battery low: {sensors['battery']}%")
        if network_status == "disconnected":
            triggered.append("🚫 Network disconnected.")

        for alert in triggered:
            self.db_tool._run("log_notification", message=f"{alert} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def load_plugins(self):
        """Load alert plugins from PLUGIN_DIR and COMPONENTS_DIR/alerts."""
        self.plugins = []
        for dir_path in [PLUGIN_DIR, os.path.join(JARVIS_DIR, "components", "alerts")]:
            if not os.path.exists(dir_path):
                continue
            for file in os.listdir(dir_path):
                if file.endswith(".py") and not file.startswith("__"):
                    plugin_path = os.path.join(dir_path, file)
                    plugin_name = os.path.splitext(file)[0]

                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                    module = importlib.util.module_from_spec(spec)

                    try:
                        spec.loader.exec_module(module)
                    except Exception as e:
                        log.error(f"[Plugin Error] Failed to load {file}: {e}")
                        continue

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseAlertPlugin) and attr != BaseAlertPlugin:
                            try:
                                instance = attr(self.db_tool, self.yahoo_tool)
                                self.plugins.append(instance)
                                log.info(f"[Plugin] Loaded: {attr.__name__} from {file}")
                            except Exception as e:
                                log.error(f"[Plugin Init Error] {attr.__name__} failed: {e}")

    def run(self):
        self.running = True
        while self.running:
            triggered = []
            try:
                self.check_stock_alerts(triggered)
                self.check_system_alerts(triggered)
                for plugin in self.plugins:
                    alerts = plugin.check_alerts()
                    if alerts:
                        triggered.extend(alerts)

                if triggered:
                    self.alert_triggered.emit(triggered)
            except Exception as e:
                log.error(f"[AlertCheck Error] {e}")

            QThread.msleep(10000)  # 10s interval

    def stop(self):
        self.running = False