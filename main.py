import os
import sys
import threading
import nltk
import requests
from jarvis import ApplicationManager, run_migrations
from config import loggers


# -------------------------- ENVIRONMENT SETUP -------------------------- #
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = "True"

log = loggers['MAIN']

# ----------------------- RESOURCE INITIALIZATION ------------------------ #
def download_nltk_resources():
    """
    Downloads required NLTK resources in the background.
    """
    try:
        log.info("🔤 Downloading NLTK resources...")
        nltk.download('punkt', quiet=True)
        nltk.download('wordnet', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('stopwords', quiet=True)
        log.info("✅ NLTK resources downloaded successfully.")
    except Exception as e:
        log.warning(f"[!] Failed to download NLTK resources: {e}")


def initialize_resources():
    """
    Runs DB migrations and launches NLTK downloader in a background thread.
    """
    try:
        log.info("🛠️ Running database migrations...")
        run_migrations()
        log.info("✅ Database migrations completed.")
    except Exception as e:
        log.error(f"[!] Migration failed: {e}")

    nltk_thread = threading.Thread(target=download_nltk_resources)
    nltk_thread.start()
    return nltk_thread

# --------------------------- TOR UTILITY --------------------------- #
def check_ip_through_proxy(proxy=None):
    """
    Checks external IP via optional proxy.
    If `proxy` is None, uses direct connection.
    """
    try:
        if proxy:
            log.info("🌍 Checking IP via Tor SOCKS5 proxy...")
            proxies = {
                'http': proxy,
                'https': proxy
            }
        else:
            log.info("🌍 Checking IP without proxy...")
            proxies = None

        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
        ip = response.json().get("origin", "Unknown")
        log.info(f"🌐 External IP: {ip}")
    except Exception as e:
        log.warning(f"[!] Failed to check IP: {e}")


# --------------------------- MAIN ENTRY POINT --------------------------- #
def main():
    log.info("🤖 Starting J.A.R.V.I.S. Virtual Assistant...")

    nltk_thread = initialize_resources()
    nltk_thread.join()

    # Attempt to verify IP through Tor (SOCKS5 on localhost:9050)
    check_ip_through_proxy()

    # Start the J.A.R.V.I.S. application
    try:
        manager = ApplicationManager()
        manager.run()
    except Exception as e:
        log.error(f"[!] J.A.R.V.I.S. failed to start: {e}")
        sys.exit(0)

if __name__ == "__main__":
    main()
