import logging
import shutil
import os
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger("BrowserDriver")

class BrowserType(Enum):
    CHROME = "chrome"
    EDGE = "edge"
    BRAVE = "brave"
    FIREFOX = "firefox"
    OTHER = "other"

class BrowserDriver:
    def __init__(self, browser_type=BrowserType.CHROME, browser_binary_paths=None):
        self.browser_type = browser_type
        self.browser_binary_paths = browser_binary_paths or {}
        self.driver = None
        self.window_handles = []
        self.current_tab_index = 0

    def _check_chrome_binary(self):
        """Check if Chrome binary exists"""
        possible_paths = [
            self.browser_binary_paths.get("chrome"),
            shutil.which("chrome"),
            shutil.which("google-chrome"),
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                logger.info(f"Found Chrome binary at: {path}")
                return path
        logger.error("Chrome binary not found. Please install Google Chrome from https://www.google.com/chrome/ or specify chrome path in config.yaml.")
        return None

    def _check_edge_binary(self):
        """Check if Edge binary exists"""
        possible_paths = [
            self.browser_binary_paths.get("edge"),
            shutil.which("msedge"),
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            "/usr/bin/microsoft-edge",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                logger.info(f"Found Edge binary at: {path}")
                return path
        logger.error("Edge binary not found. Please install Microsoft Edge from https://www.microsoft.com/edge/ or specify edge path in config.yaml.")
        return None

    def _check_brave_binary(self):
        """Check if Brave binary exists"""
        possible_paths = [
            self.browser_binary_paths.get("brave"),
            shutil.which("brave"),
            shutil.which("brave-browser"),
            "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "/usr/bin/brave-browser",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                logger.info(f"Found Brave binary at: {path}")
                return path
        logger.error("Brave binary not found. Please install Brave from https://brave.com/download/ or specify brave path in config.yaml.")
        return None

    def _check_firefox_binary(self):
        """Check if Firefox binary exists"""
        possible_paths = [
            self.browser_binary_paths.get("firefox"),
            shutil.which("firefox"),
            "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
            "/usr/bin/firefox",
            "/usr/local/bin/firefox",
            "/Applications/Firefox.app/Contents/MacOS/firefox"
        ]
        for path in possible_paths:
            if path and os.path.exists(path):
                logger.info(f"Found Firefox binary at: {path}")
                return path
        logger.error("Firefox binary not found. Please install Firefox from https://www.mozilla.org/firefox/ or specify firefox path in config.yaml.")
        return None

    def setup(self, headless=True, incognito=True, fallback_browsers=None):
        """Setup browser with automatic driver download and fallback"""
        fallback_browsers = fallback_browsers or []
        try:
            if self.browser_type == BrowserType.CHROME:
                chrome_binary = self._check_chrome_binary()
                if not chrome_binary and fallback_browsers:
                    logger.warning("Chrome binary not found, attempting fallback")
                    return self._try_fallback(fallback_browsers, headless, incognito)
                elif not chrome_binary:
                    raise WebDriverException("Chrome binary not found. Install Chrome or configure chrome path.")

                options = webdriver.ChromeOptions()
                if chrome_binary:
                    options.binary_location = chrome_binary
                if headless:
                    options.add_argument("--headless")
                if incognito:
                    options.add_argument("--incognito")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                service = ChromeService(ChromeDriverManager().install())
                logger.info("ChromeDriver installed or verified")
                self.driver = webdriver.Chrome(service=service, options=options)

            elif self.browser_type == BrowserType.EDGE:
                edge_binary = self._check_edge_binary()
                if not edge_binary and fallback_browsers:
                    logger.warning("Edge binary not found, attempting fallback")
                    return self._try_fallback(fallback_browsers, headless, incognito)
                elif not edge_binary:
                    raise WebDriverException("Edge binary not found. Install Edge or configure edge path.")

                options = webdriver.EdgeOptions()
                if edge_binary:
                    options.binary_location = edge_binary
                if headless:
                    options.add_argument("--headless")
                if incognito:
                    options.add_argument("--inprivate")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                service = EdgeService(EdgeChromiumDriverManager().install())
                logger.info("EdgeDriver installed or verified")
                self.driver = webdriver.Edge(service=service, options=options)

            elif self.browser_type == BrowserType.BRAVE:
                brave_binary = self._check_brave_binary()
                if not brave_binary and fallback_browsers:
                    logger.warning("Brave binary not found, attempting fallback")
                    return self._try_fallback(fallback_browsers, headless, incognito)
                elif not brave_binary:
                    raise WebDriverException("Brave binary not found. Install Brave or configure brave path.")

                options = webdriver.ChromeOptions()
                if brave_binary:
                    options.binary_location = brave_binary
                if headless:
                    options.add_argument("--headless")
                if incognito:
                    options.add_argument("--incognito")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                service = ChromeService(ChromeDriverManager().install())
                logger.info("ChromeDriver installed or verified for Brave")
                self.driver = webdriver.Chrome(service=service, options=options)

            elif self.browser_type == BrowserType.FIREFOX:
                firefox_binary = self._check_firefox_binary()
                if not firefox_binary and fallback_browsers:
                    logger.warning("Firefox binary not found, attempting fallback")
                    return self._try_fallback(fallback_browsers, headless, incognito)
                elif not firefox_binary:
                    raise WebDriverException("Firefox binary not found. Install Firefox or configure firefox path.")

                options = webdriver.FirefoxOptions()
                if firefox_binary:
                    options.binary_location = firefox_binary
                if headless:
                    options.add_argument("--headless")
                if incognito:
                    options.add_argument("-private")
                service = FirefoxService(GeckoDriverManager().install())
                logger.info("GeckoDriver installed or verified")
                self.driver = webdriver.Firefox(service=service, options=options)

            elif self.browser_type == BrowserType.OTHER:
                raise ValueError("Custom browser type 'other' requires specific implementation")

            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            self.driver.maximize_window()
            self.window_handles = self.driver.window_handles
            logger.info(f"Initialized {self.browser_type.value} browser")

        except WebDriverException as e:
            logger.error(f"Failed to setup {self.browser_type.value} browser: {e}")
            if fallback_browsers:
                logger.info(f"Retrying with fallback browsers: {[b.value for b in fallback_browsers]}")
                return self._try_fallback(fallback_browsers, headless, incognito)
            raise

        except Exception as e:
            logger.error(f"Unexpected error during browser setup: {e}")
            raise

    def _try_fallback(self, fallback_browsers, headless, incognito):
        """Attempt to setup a fallback browser"""
        for fallback in fallback_browsers:
            logger.info(f"Attempting fallback to {fallback.value}")
            self.browser_type = fallback
            try:
                self.setup(headless, incognito, fallback_browsers[fallback_browsers.index(fallback)+1:])
                return
            except Exception as e:
                logger.error(f"Fallback to {fallback.value} failed: {e}")
        raise WebDriverException("All browser setups failed. Please install a supported browser.")

    def navigate_to(self, url):
        self.driver.get(url)
        self.window_handles = self.driver.window_handles
        self.current_tab_index = self.get_current_tab_index()

    def open_new_window(self, url=None, name=None):
        self.driver.execute_script("window.open('');")
        self.window_handles = self.driver.window_handles
        self.current_tab_index = len(self.window_handles) - 1
        self.driver.switch_to.window(self.window_handles[self.current_tab_index])
        if url:
            self.navigate_to(url)
        if name:
            self.driver.execute_script(f"window.name = '{name}'")

    def switch_to_window(self, name):
        for handle in self.window_handles:
            self.driver.switch_to.window(handle)
            if self.driver.execute_script("return window.name") == name or handle == name:
                self.current_tab_index = self.window_handles.index(handle)
                return
        raise ValueError(f"Window {name} not found")

    def switch_to_tab(self, action):
        if action == "next":
            self.current_tab_index = (self.current_tab_index + 1) % len(self.window_handles)
        elif action == "previous":
            self.current_tab_index = (self.current_tab_index - 1) % len(self.window_handles)
        self.driver.switch_to.window(self.window_handles[self.current_tab_index])

    def close_window(self, name=None):
        if name:
            self.switch_to_window(name)
        self.driver.close()
        self.window_handles = self.driver.window_handles
        self.current_tab_index = min(self.current_tab_index, len(self.window_handles) - 1)
        if self.window_handles:
            self.driver.switch_to.window(self.window_handles[self.current_tab_index])

    def go_back(self):
        self.driver.back()

    def get_current_tab_index(self):
        try:
            current_handle = self.driver.current_window_handle
            return self.window_handles.index(current_handle)
        except:
            return 0

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.window_handles = []
            self.current_tab_index = 0
            logger.info(f"Closed {self.browser_type.value} browser")

if __name__ == "__main__":
    browser = BrowserDriver()
    browser.setup(headless=False, incognito=True, fallback_browsers=[BrowserType.BRAVE, BrowserType.EDGE, BrowserType.FIREFOX])
    driver = browser.driver
    driver.get("https://grok.com/chat/520d69cf-132c-47da-8a09-fcba0c84d148")