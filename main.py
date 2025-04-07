import os
import sys
import platform
import threading
import subprocess
import time
import requests
import nltk,dotenv
from jarvis import ApplicationManager, run_migrations
from config import loggers,VERSION
import warnings

dotenv.load_dotenv()
warnings.filterwarnings("ignore")

# --------------------------- ENVIRONMENT SETUP --------------------------- #
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = "True"
os.environ['USER_AGENT']="langchain-framework"
log = loggers['MAIN']

# --------------------------- SYSTEM UTILITIES --------------------------- #
def print_system_info():
    log.info("🧠 System Diagnostics:")
    log.info(f"   🖥️ OS        : {platform.system()} {platform.release()}")
    log.info(f"   🐍 Python    : {platform.python_version()}")
    log.info(f"   📂 Directory : {os.getcwd()}")
    log.info(f"      J.A.R.V.I.S: {VERSION}    ")


def check_internet(timeout=5):
    try:
        log.info("🌐 Checking internet connectivity...")
        requests.get("http://example.com", timeout=timeout)
        log.info("✅ Internet connection is active.")
        return True
    except requests.RequestException:
        log.error("❌ No internet connection.")
        return False


def download_nltk_resources():
    try:
        log.info("📥 Downloading NLTK resources...")
        nltk.download('punkt', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('stopwords', quiet=True)
        log.info("✅ NLTK resources ready.")
    except Exception as e:
        log.warning(f"[!] NLTK download error: {e}")


def initialize_resources():
    try:
        log.info("🛠️ Running database migrations...")
        run_migrations()
        log.info("✅ Migrations completed.")
    except Exception as e:
        log.error(f"[!] Migration failed: {e}")
        sys.exit(1)

    thread = threading.Thread(target=download_nltk_resources, daemon=True)
    thread.start()
    return thread


# --------------------------- TOR FUNCTIONS --------------------------- #
def is_tor_running():
    try:
        res = requests.get("http://httpbin.org/ip", proxies={"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}, timeout=5)
        return True
    except:
        return False


def launch_tor():
    log.info("🕵️ Tor not running. Attempting to start Tor...")

    if platform.system() == "Windows":
        tor_path = os.path.expandvars(r"%ProgramFiles%\Tor Browser\Browser\TorBrowser\Tor\tor.exe")
        if not os.path.exists(tor_path):
            tor_path = os.path.expandvars(r"%ProgramFiles(x86)%\Tor Browser\Browser\TorBrowser\Tor\tor.exe")
        if not os.path.exists(tor_path):
            log.error("❌ Could not find Tor executable. Please install Tor Browser.")
            return False

        subprocess.Popen([tor_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif platform.system() in ["Linux", "Darwin"]:
        try:
            subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            log.error("❌ Tor not installed. Install with: sudo apt install tor")
            return False
    else:
        log.error("❌ Unsupported OS for auto-starting Tor.")
        return False

    # Wait for Tor to become ready
    for _ in range(10):
        if is_tor_running():
            log.info("✅ Tor started and is running.")
            return True
        time.sleep(1)

    log.error("❌ Tor failed to start.")
    return False


def check_ip_through_proxy(proxy=None, label="Direct"):
    try:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        log.info(f"🌍 Checking IP via {label} connection...")
        res = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
        ip = res.json().get("origin", "Unknown")
        log.info(f"🌐 {label} IP: {ip}")
    except Exception as e:
        log.warning(f"[!] {label} IP check failed: {e}")


# --------------------------- MAIN FUNCTION --------------------------- #
def main():
    log.info("🤖 Launching J.A.R.V.I.S. Virtual Assistant...")
    print_system_info()

    if not check_internet():
        sys.exit("🚫 Please connect to the internet and restart the assistant.")

    nltk_thread = initialize_resources()

    # Check or Start Tor
    if not is_tor_running():
        if not launch_tor():
            log.warning("⚠️ Continuing without Tor routing.")
        else:
            time.sleep(3)

    # IP Check
    check_ip_through_proxy(label="Direct")
    if is_tor_running():
        check_ip_through_proxy("socks5h://127.0.0.1:9050", label="Tor")

    nltk_thread.join(timeout=15)

    try:
        manager = ApplicationManager()
        manager.run()
    except Exception as e:
        log.error(f"[!] J.A.R.V.I.S. failed to start: {e}")
        sys.exit(1)


# --------------------------- ENTRY POINT --------------------------- #
if __name__ == "__main__":
    main()