from core.browserNode.driver import BrowserType, BrowserDriver
from core.Agent_models import get_model_from_database as get_model
import html2text
from selenium.webdriver.common.by import By
from interpreter import OpenInterpreter
import time
from bs4 import BeautifulSoup
import re
from typing import Literal
import pytesseract
from PIL import Image
from io import BytesIO
import base64

class GoogleSearch(BrowserDriver):
    def __init__(self):
        super().__init__()
        self.setup(headless=False, incognito=True)
        self.history = []
        self.window_map = {}  # Track named windows

    def analyze_page(self, intent):
        html_content = self.driver.page_source
        text_content = html2text.html2text(html_content)

        elements = (
            self.driver.find_elements(By.TAG_NAME, "a")
            + self.driver.find_elements(By.TAG_NAME, "button")
            + self.driver.find_elements(By.TAG_NAME, "input")
            + self.driver.find_elements(By.TAG_NAME, "select")
        )

        elements_info = [
            {
                "id": idx,
                "text": elem.text,
                "attributes": elem.get_attribute("outerHTML"),
            }
            for idx, elem in enumerate(elements)
        ]

        ai_query = f"""
        Below is the content of the current webpage along with interactive elements. 
        Given the intent "{intent}", please extract useful information and provide sufficient details 
        about interactive elements, focusing especially on those pertinent to the provided intent.

        If the information requested by the intent "{intent}" is present on the page, simply return that.

        If not, return the top 10 most relevant interactive elements in a concise, actionable format, listing them on separate lines
        with their ID, a description, and their possible action.

        Do not hallucinate.

        Page Content:
        {text_content}

        Interactive Elements:
        {elements_info}
        """

        interpreter = OpenInterpreter()
        interpreter.llm.model = f"openai/{get_model().name}"
        interpreter.llm.api_base = get_model().url
        interpreter.llm.api_key = get_model().api_key
        response = interpreter.computer.ai.chat(ai_query)

        return response

    def go_to_url(self, url):
        if not url.startswith("https://") and not url.startswith("http://"):
            url = f"https://{url}"
        self.driver.get(url)
        while True:
            break_system=self.solve_captcha_if_present()
            if not break_system:
                break
        self.history.append({"command": f"Visited {url}", "clicked": None})
        time.sleep(3)

    def extract_clickable_elements(self) -> list[dict]:
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        buttons = soup.find_all(['button', 'a', 'input','select'])
        elements = []
        for tag in buttons:
            if tag.name == "input" and tag.get("type") != "submit":
                continue
            label = tag.get_text(strip=True) or tag.get("aria-label") or tag.get("value") or ""
            if label:
                elements.append({
                    "tag": tag.name,
                    "text": label,
                    "id": tag.get("id"),
                    "class": tag.get("class"),
                })
        return elements

    def ask_llm_which_button(self, elements: list[dict], command: str) -> dict:
        prompt = f"""
        You are given a list of buttons and links extracted from a website.
        The user said: "{command}"

        Here are the available elements:
        """

        for i, el in enumerate(elements):
            label = el['text']
            prompt += f"{i + 1}. Tag: {el['tag']} | Label: {label} | ID: {el['id']} | Class: {el['class']}\n"

        prompt += "\nWhich one best matches the user's command? Return the index only."

        interpreter = OpenInterpreter()
        interpreter.llm.model = f"openai/{get_model().name}"
        interpreter.llm.api_base = get_model().url
        interpreter.llm.api_key = get_model().api_key
        response = interpreter.computer.ai.chat(prompt)

        response = re.sub(r'<.*?>', '', response)
        numbers = re.findall(r'\d+', response)
        if not numbers:
            raise ValueError("LLM did not return a valid index.")
        index = int(numbers[0]) - 1
        return elements[index]

    def click_element(self, element: dict):
        try:
            if element['id']:
                self.driver.find_element(By.ID, element['id']).click()
            elif element['class']:
                self.driver.find_element(By.CLASS_NAME, element['class'][0]).click()
            elif element['text']:
                self.driver.find_element(By.XPATH, f"//*[contains(text(), '{element['text']}')]").click()
            time.sleep(2)
        except Exception as e:
            print(f"Failed to click: {e}")

    def execute_command(self, url: str, user_command: str):
        i=len(self.window_map)
        #self.open_new_window(url,f"JARVIS-{i}")
        #time.sleep(25)
        self.go_to_url(url)
        elements = self.extract_clickable_elements()
        selected = self.ask_llm_which_button(elements, user_command)
        if selected:
            self.click_element(selected)
            self.history.append({"command": user_command, "clicked": selected})

    def open_new_tab(self, url=None):
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        if url:
            self.driver.get(url)
        self.history.append({"command": f"Opened new tab with {url}" if url else "Opened new tab"})

    def go_back(self):
        if self.history:
            self.driver.back()
            self.history.pop()
            time.sleep(2)

    def switch_to_tab(self, action: Literal["previous", "next"] = "next"):
        index = self.get_current_tab_index()
        index += -1 if action == "previous" else 1
        handles = self.driver.window_handles
        if 0 <= index < len(handles):
            self.driver.switch_to.window(handles[index])
            self.history.append({"command": f"Switched to tab {index}"})

    def get_current_tab_index(self):
        current_handle = self.driver.current_window_handle
        index = self.driver.window_handles.index(current_handle)
        self.history.append({"command": f"Current tab index: {index}"})
        return index

    def open_new_window(self, url=None, name=None):
        self.driver.execute_script("window.open('', '_blank');")
        new_handle = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_handle)
        if name:
            self.window_map[name] = new_handle
        if url:
            self.driver.get(url)
        self.history.append({"command": f"Opened new window: {url if url else 'blank'}"})

    def switch_to_window(self, name):
        if name in self.window_map:
            self.driver.switch_to.window(self.window_map[name])
            print(f"Switched to window: {name}")
        else:
            print(f"No window found with name: {name}")

    def close_window(self, name):
        if name in self.window_map:
            handle = self.window_map[name]
            if handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                self.driver.close()
                del self.window_map[name]
                self.history.append({"command":f"Closed window: {name}"})
            else:
                self.history.append({"command": f"Window '{name}' already closed."})
        else:
            print(f"No window found with name: {name}")

    def solve_captcha_if_present(self):
        try:
            print("[INFO] Checking for CAPTCHA...")
            html = self.driver.page_source.lower()
            soup = BeautifulSoup(html, 'html.parser')

            if 'captcha' not in html and 'verify' not in html:
                return True  # No captcha

            # Check for iframe with reCAPTCHA
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                src = frame.get_attribute("src")
                if src and "recaptcha" in src:
                    print("[INFO] reCAPTCHA detected. Manual verification might be required.")
                    return False

            # Attempt OCR-based CAPTCHA resolution
            images = soup.find_all('img')
            for img in images:
                src = img.get('src')
                if src and ('captcha' in src.lower() or 'verify' in src.lower()):
                    try:
                        if src.startswith('data:image'):
                            header, base64_data = src.split(',', 1)
                            image_data = base64.b64decode(base64_data)
                            image = Image.open(BytesIO(image_data))
                        else:
                            self.driver.get(src)
                            time.sleep(2)
                            screenshot = self.driver.get_screenshot_as_png()
                            image = Image.open(BytesIO(screenshot))

                        captcha_text = pytesseract.image_to_string(image).strip()
                        print("[OCR CAPTCHA TEXT]", captcha_text)

                        prompt = f"Given the CAPTCHA text image result: '{captcha_text}', what value should be entered to solve it?"
                        interpreter = OpenInterpreter()
                        model = get_model()
                        interpreter.llm.model = f"openai/{model.name}"
                        interpreter.llm.api_base = model.url
                        interpreter.llm.api_key = model.api_key
                        solution = interpreter.computer.ai.chat(prompt)

                        # Enter the CAPTCHA solution into any visible text input
                        input_fields = self.driver.find_elements(By.TAG_NAME, "input")
                        for field in input_fields:
                            name = field.get_attribute("name") or ""
                            if "captcha" in name.lower() or "verify" in name.lower():
                                field.clear()
                                field.send_keys(solution.strip())
                                print("[INFO] CAPTCHA solution entered.")
                                return True

                        print("[INFO] CAPTCHA solution received but could not find input field.")
                        return False

                    except Exception as e:
                        print("[ERROR] CAPTCHA processing failed:", e)
                        return False

            print("[INFO] CAPTCHA detected but not solved. Might need manual intervention.")
            return False

        except Exception as e:
            print(f"[ERROR] solve_captcha_if_present failed: {e}")
            return False

if __name__ == "__main__":
    g = GoogleSearch()
    g.execute_command("https://www.google.com/search?q=google+engine&source=desktop", "Click the first website")
