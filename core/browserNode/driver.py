import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from enum import Enum


# Setup logger
logger = logging.getLogger("BrowserDriver")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class BrowserType(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"


class BrowserDriver:
    def __init__(self, browser_type=BrowserType.CHROME):
        self._driver = None
        self.browser_type = browser_type

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            self.setup()
        return self._driver

    @driver.setter
    def driver(self, value):
        self._driver = value

    def setup(self, headless=True, incognito=False, user_agent=None):
        """Setup browser driver with fallbacks"""
        try:
            if self.browser_type == BrowserType.FIREFOX:
                self._setup_firefox(headless, user_agent)
            elif self.browser_type == BrowserType.EDGE:
                self._setup_edge(headless)
            else:
                self._setup_chrome(headless, incognito, user_agent)
        except Exception as e:
            logger.warning(f"{self.browser_type.value.title()} setup failed: {e}. Falling back to Chrome.")
            self._setup_chrome(headless, incognito, user_agent)

    def _setup_chrome(self, headless, incognito, user_agent):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        if incognito:
            options.add_argument("--incognito")
        if user_agent:
            options.add_argument(f"user-agent={user_agent}")

        service = ChromeService(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=options)
        logger.info("Initialized Chrome WebDriver.")

    def _setup_firefox(self, headless, user_agent):
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        profile = webdriver.FirefoxProfile()
        if user_agent:
            profile.set_preference("general.useragent.override", user_agent)

        service = FirefoxService(GeckoDriverManager().install())
        self._driver = webdriver.Firefox(service=service, options=options, firefox_profile=profile)
        logger.info("Initialized Firefox WebDriver.")

    def _setup_edge(self, headless):
        options = webdriver.EdgeOptions()
        if headless:
            options.add_argument("--headless")

        service = EdgeService(EdgeChromiumDriverManager().install())
        self._driver = webdriver.Edge(service=service, options=options)
        logger.info("Initialized Edge WebDriver.")


    def quit(self):
        """Close the browser"""
        if self._driver:
            self._driver.quit()
            logger.info("Browser closed.")
            self._driver = None

if __name__ == "__main__":
    browser = BrowserDriver(browser_type=BrowserType.FIREFOX)
    browser.setup(headless=True, incognito=True, user_agent="MyBot/1.0")
    driver = browser.driver
    driver.get("https://google.com")
    print(driver.title)
    browser.quit()
