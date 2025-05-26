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
import os.path
import dotenv
import warnings
import time

# --------------------------- ENVIRONMENT --------------------------- #
dotenv.load_dotenv()
warnings.filterwarnings("ignore")

# --------------------------- SYSTEM UTILITIES --------------------------- #
def print_system_info(log):
    from config import VERSION
    import platform
    import os
    log.info("🧠 System Diagnostics:")
    log.info(f"   🖥️ OS        : {platform.system()} {platform.release()}")
    log.info(f"   🐍 Python    : {platform.python_version()}")
    log.info(f"   📂 Directory : {os.getcwd()}")
    log.info(f"   🤖 J.A.R.V.I.S: {VERSION}")

def check_internet(log, timeout=5):
    import requests
    try:
        log.info("🌐 Checking internet connectivity...")
        requests.get("http://example.com", timeout=timeout)
        log.info("✅ Internet connection is active.")
        return True
    except requests.RequestException:
        log.error("❌ No internet connection.")
        return False

def download_nltk_resources(log,splash):
    from nltk import download
    try:
        log.info("📥 Downloading NLTK resources...")
        splash.update_message("📥 Downloading NLTK resources...",60)
        download('punkt', quiet=True)
        download('wordnet', quiet=True)
        download('averaged_perceptron_tagger', quiet=True)
        download('stopwords', quiet=True)
        log.info("✅ NLTK resources ready.")
        splash.update_message("✅ NLTK resources ready.",65)
    except Exception as e:
        log.warning(f"[!] NLTK download error: {e}")

def initialize_resources(log,splash):
    from jarvis import run_migrations
    import sys
    try:
        log.info("🛠️ Running database migrations...")
        splash.update_message("🛠️ Running database migrations",50)
        run_migrations()
        log.info("✅ Migrations completed.")
        splash.update_message("✅ Migrations completed.",55)
    except Exception as e:
        log.error(f"[!] Migration failed: {e}")
        sys.exit(1)

    download_nltk_resources(log,splash)

# --------------------------- TOR FUNCTIONS --------------------------- #
def is_tor_running():
    import requests
    try:
        requests.get("http://httpbin.org/ip",
                     proxies={"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}, timeout=5)
        return True
    except:
        return False

def launch_tor(log):
    import platform
    import os
    import subprocess
    import time
    log.info("🕵️ Tor not running. Attempting to start Tor...")
    try:
        if platform.system() == "Windows":
            tor_paths = [
                os.path.expandvars(r"%ProgramFiles%\Tor Browser\Browser\TorBrowser\Tor\tor.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Tor Browser\Browser\TorBrowser\Tor\tor.exe")
            ]
            for path in tor_paths:
                if os.path.exists(path):
                    subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
            else:
                raise FileNotFoundError("Tor executable not found")
        elif platform.system() in ["Linux", "Darwin"]:
            subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            raise EnvironmentError("Unsupported OS for Tor auto-start")

        for _ in range(10):
            if is_tor_running():
                log.info("✅ Tor started and is running.")
                return True
            time.sleep(1)

        raise TimeoutError("Tor did not start in time")
    except Exception as e:
        log.error(f"❌ Tor startup failed: {e}")
        return False

def check_ip_through_proxy(log, proxy=None, label="Direct"):
    import requests
    try:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        log.info(f"🌍 Checking IP via {label} connection...")
        res = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
        ip = res.json().get("origin", "Unknown")
        log.info(f"🌐 {label} IP: {ip}")
    except Exception as e:
        log.warning(f"[!] {label} IP check failed: {e}")

def set_env(key, value):
    dotenv.set_key(".env", key, value)

def launch_cli():
    from components.coder.cli.console_terminal import  MAIN_COLOR
    from rich.console import Console
    from rich.markdown import Markdown
    from InquirerPy import inquirer
    from argparse import ArgumentParser
    console = Console()
    try:
        markdown_text = """
        # 🚀 Welcome to J.A.R.V.I.S

        **J.A.R.V.I.S** is a modular AI system with the following capabilities:

        - ✅ Natural Language Understanding
        - 🧠 Autonomous Agent Collaboration
        - 🔐 Tor-enabled Secure Communication
        - 🛠️ Developer Tools (CLI + GUI)

        > “The future is here.”

        ---  
        Built with ❤️ using Python.
        """

        md = Markdown("[green]" + markdown_text)
        console.print(md)

        parser = ArgumentParser(description='J.A.R.V.I.S. CLI Mode')
        parser.add_argument('--coder', action='store_true', help="🤖 AI-powered code generation")
        parser.add_argument('--interpreter', action='store_true', help="Natural language interface for computers")
        parser.add_argument("--settings", action="store_true", help="Settings of the JARVIS CLI")
        args = parser.parse_args()
        if args.coder:
            from terminal.coder import coder_
            coder_()

        elif args.interpreter:
            from terminal.interpreter import inter
            inter()

        elif args.settings:
            from terminal.settings.llm_selection import llm, LLM_TYPE
            llm_type, base_url, api_key, selected_model = llm(console)
            set_env("ENDPOINT", llm_type.value)

            if llm_type == LLM_TYPE.OPENAI:
                set_env("OPENAI_API_MODEL", selected_model)
                set_env("OPENAI_API_KEY", api_key)
                if base_url is not None:
                    set_env("OPENAI_BASE_URL", base_url)

            elif llm_type == LLM_TYPE.OLLAMA:
                set_env("OLLAMA_MODEL", selected_model)
                set_env("OLLAMA_ENDPOINT", base_url)

            elif llm_type == LLM_TYPE.GROQ:
                set_env('GROQ_API_KEY', api_key)
                set_env('GROQ_API_MODEL', selected_model)

            elif llm_type == LLM_TYPE.ANTHROPIC:
                set_env('ANTHROPIC_API_KEY', api_key)
                set_env('ANTHROPIC_MODEL', selected_model)

            elif llm_type == LLM_TYPE.AZURE:
                set_env("AZURE_OPENAI_API_KEY", api_key)

            console.print("Settings Saved Successfully")
            mode = inquirer.select(
                "Select the Mode:",
                choices=[
                    "Interpreter",
                    "J.A.R.V.I.S. Coder",
                ],
                default="J.A.R.V.I.S. Coder"
            ).execute()
            if "J.A.R.V.I.S. Coder" in mode:
                from terminal.coder import coder_
                coder_()
            elif "Interpreter" in mode:
                from terminal.interpreter import inter
                inter()
    except (KeyboardInterrupt or Exception) as e:
        console.print(
            f"Thank you for using J.A.R.V.I.S. CLI! See you next time! :bye:",
            style=f"{MAIN_COLOR} bold",
        )

# --------------------------- MAIN FUNCTION --------------------------- #
def main(start):
    from sys import argv, exit
    from time import sleep
    from PyQt5.QtWidgets import QApplication
    from gui.splash_screen import SplashScreen
    import time

    try:
        if len(argv) > 1:
            launch_cli()
        else:
            print(f"[⏱️]  Initialized in {time.time() - start:.2f}s")
            from config import loggers, JARVIS_DIR
            log = loggers['MAIN']
            log.info("🤖 Launching J.A.R.V.I.S. Virtual Assistant...")

            app = QApplication(argv)
            splash = SplashScreen(os.path.join(JARVIS_DIR, "assests", "splash-jarvis-logo.jpg"))
            splash.show()
            app.processEvents()

            splash.update_message("Gathering System Info", 10)
            print_system_info(log)

            splash.update_message("Checking Internet Connection", 20)
            if not check_internet(log):
                exit("🚫 Please connect to the internet and restart the assistant.")

            splash.update_message("Initializing Resources", 40)
            initialize_resources(log,splash)

            splash.update_message("Checking Tor Service", 70)
            if not is_tor_running():
                if not launch_tor(log):
                    log.warning("⚠️ Continuing without Tor routing.")
                    splash.update_message("⚠️ Continuing without Tor routing", 70)
                else:
                    sleep(3)
            else:
                splash.update_message("Tor not available", 70)
                sleep(2)

            splash.update_message("Verifying IP Settings", 90)
            check_ip_through_proxy(label="Direct", log=log)
            if is_tor_running():
                check_ip_through_proxy(proxy="socks5h://127.0.0.1:9050", label="Tor", log=log)

            splash.update_message("Launching Interface", 100)
            from jarvis import ApplicationManager
            manager = ApplicationManager()
            splash.finish(manager.current_page)
            manager.run()

    except KeyboardInterrupt:
        print("Goodbye!")

# --------------------------- ENTRY POINT --------------------------- #
if __name__ == "__main__":
    start = time.time()
    main(start)