# Copyright 2025 xAI
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
import sqlite3
import json
import hashlib
import requests
from datetime import datetime
from collections import defaultdict, deque
from typing import  Optional
import threading
import time
from crewai import Agent, Task, Crew,LLM
from crewai_tools import (
    WebsiteSearchTool, FileReadTool, BaseTool, ScrapeWebsiteTool,
    DirectoryReadTool, SerperDevTool, TXTSearchTool, EXASearchTool,
    CodeDocsSearchTool, CodeInterpreterTool, CSVSearchTool, DOCXSearchTool,
    DirectorySearchTool, JSONSearchTool, MDXSearchTool, PDFSearchTool,
 ScrapeElementFromWebsiteTool, SeleniumScrapingTool,
    XMLSearchTool, YoutubeChannelSearchTool, YoutubeVideoSearchTool
)
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
import yfinance as yf
from config import JARVIS_DIR,SESSION_PATH
from core.Agent_models import get_model_from_database
from core.memory.memory_agent import MemorySettings
import inspect

# Initialize LLM and Mem0
llm = LLM(
    model=get_model_from_database().name,
    api_key=get_model_from_database().api_key,
    base_url=get_model_from_database().url
)
mem0 = MemorySettings()
mem0._initialize_memory()

# Exchange rates
EXCHANGE_RATES = {
    "USD": 1.0,
    "INR": 83.0,
    "EUR": 0.85,
    "GBP": 0.73
}

# Database setup
db_path = os.path.join(JARVIS_DIR, "data", "assistant_data.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS request_history (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, request TEXT, response TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS confidential_notes (file_path TEXT PRIMARY KEY, note TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS contacts (name TEXT PRIMARY KEY, role TEXT, contact_info TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks_status (task_id TEXT PRIMARY KEY, status TEXT, result TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS cache (request_hash TEXT PRIMARY KEY, response TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS long_term_memory (key TEXT PRIMARY KEY, value TEXT, timestamp TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS portfolio (ticker TEXT PRIMARY KEY, company TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY, company TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (ticker TEXT PRIMARY KEY, company TEXT, purchase_price REAL, quantity INTEGER, currency TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (ticker TEXT, target_price REAL, currency TEXT, PRIMARY KEY (ticker, target_price))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS price_history (ticker TEXT, date TEXT, price REAL, currency TEXT, PRIMARY KEY (ticker, date))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS mem0_interactions (user_id TEXT, query TEXT, response TEXT, timestamp TEXT)''')
conn.commit()

# Short-term memory
class ShortTermMemory:
    def __init__(self, max_size=100):
        self.memory = deque(maxlen=max_size)

    def add(self, key, value):
        self.memory.append((key, value))

    def get(self, key):
        for k, v in self.memory:
            if k == key:
                return v
        return None

    def clear(self):
        self.memory.clear()

short_term_memory = ShortTermMemory()

class SecureContactManagerTool(BaseTool):
    name: str = "SecureContactManager"
    description: str = "Manages a secure list of key contacts in the database."

    def _run(self, action: str, **kwargs) -> str:
        if action == "add":
            name = kwargs.get("name")
            role = kwargs.get("role")
            contact_info = kwargs.get("contact_info")
            if name and role and contact_info:
                cursor.execute("INSERT OR REPLACE INTO contacts (name, role, contact_info) VALUES (?, ?, ?)",
                               (name, role, contact_info))
                conn.commit()
                short_term_memory.add(f"contact_{name}", f"{role}, {contact_info}")
                return f"Contact {name} added successfully."
            return "Error: Missing contact details."
        elif action == "retrieve":
            name = kwargs.get("name")
            cached = short_term_memory.get(f"contact_{name}")
            if cached:
                return f"Contact: {name}, {cached}"
            cursor.execute("SELECT role, contact_info FROM contacts WHERE name = ?", (name,))
            result = cursor.fetchone()
            if result:
                short_term_memory.add(f"contact_{name}", f"{result[0]}, {result[1]}")
                return f"Contact: {name}, Role: {result[0]}, Info: {result[1]}"
            return "Contact not found."
        elif action == "list":
            cursor.execute("SELECT name, role FROM contacts")
            contacts = cursor.fetchall()
            return "\n".join([f"{name}: {role}" for name, role in contacts]) or "No contacts."
        return "Invalid action."

class EncryptDataTool(BaseTool):
    name: str = "EncryptDataTool"
    description: str = "Encrypts sensitive data using SHA-256 hashing."

    def _run(self, data: str) -> str:
        encrypted = hashlib.sha256(data.encode()).hexdigest()
        short_term_memory.add(f"encrypted_{data[:10]}", encrypted)
        return encrypted

class APICallTool(BaseTool):
    name: str = "APICallTool"
    description: str = "Makes HTTP requests to external APIs with caching."

    def _run(self, url: str, method: str = "GET", headers: dict = None, data: dict = None) -> str:
        request_key = hashlib.md5(f"{url}{method}{json.dumps(headers)}{json.dumps(data)}".encode()).hexdigest()
        cached_short = short_term_memory.get(request_key)
        if cached_short:
            return cached_short
        cursor.execute("SELECT response FROM cache WHERE request_hash = ?", (request_key,))
        cached_long = cursor.fetchone()
        if cached_long:
            short_term_memory.add(request_key, cached_long[0])
            return cached_long[0]
        try:
            response = requests.request(method, url, headers=headers, json=data)
            result = response.text
            cursor.execute("INSERT OR REPLACE INTO cache (request_hash, response) VALUES (?, ?)", (request_key, result))
            short_term_memory.add(request_key, result)
            conn.commit()
            return result
        except Exception as e:
            return f"API call failed: {str(e)}"

class TaskTrackerTool(BaseTool):
    name: str = "TaskTrackerTool"
    description: str = "Tracks task status and results in the database."

    def _run(self, task_id: str, status: str = None, result: str = None) -> str:
        if status:
            cursor.execute("INSERT OR REPLACE INTO tasks_status (task_id, status, result) VALUES (?, ?, ?)",
                           (task_id, status, result or ""))
            conn.commit()
            short_term_memory.add(f"task_{task_id}", f"{status}: {result}")
            return f"Task {task_id} updated to {status}"
        cached = short_term_memory.get(f"task_{task_id}")
        if cached:
            return f"Task {task_id}: {cached}"
        cursor.execute("SELECT status, result FROM tasks_status WHERE task_id = ?", (task_id,))
        result = cursor.fetchone()
        if result:
            short_term_memory.add(f"task_{task_id}", f"{result[0]}: {result[1]}")
            return f"Task {task_id}: {result[0]} - {result[1]}"
        return "Task not found."

class MemoryManagerTool(BaseTool):
    name: str = "MemoryManagerTool"
    description: str = "Manages long-term and short-term memory, including Mem0 integration."

    def _run(self, action: str, key: str, value: str = None, user_id: str = None) -> str:
        if action == "store_long":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT OR REPLACE INTO long_term_memory (key, value, timestamp) VALUES (?, ?, ?)",
                           (key, value, timestamp))
            conn.commit()
            return f"Stored {key} in long-term memory."
        elif action == "retrieve_long":
            cursor.execute("SELECT value FROM long_term_memory WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else "Not found in long-term memory."
        elif action == "store_short":
            short_term_memory.add(key, value)
            return f"Stored {key} in short-term memory."
        elif action == "retrieve_short":
            result = short_term_memory.get(key)
            return result if result else "Not found in short-term memory."
        elif action == "store_mem0":
            if user_id and value:
                mem0.add_memory([{"role": "user", "content": key}, {"role": "assistant", "content": value}], user_id=user_id)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("INSERT INTO mem0_interactions (user_id, query, response, timestamp) VALUES (?, ?, ?, ?)",
                               (user_id, key, value, timestamp))
                conn.commit()
                return f"Stored in Mem0 for user {user_id}."
            return "Error: Missing user_id or value."
        elif action == "retrieve_mem0":
            if user_id:
                memories = mem0.search_memory(key, limit=5)
                return ' '.join([mem["memory"] for mem in memories]) or "No memories found."
            return "Error: Missing user_id."
        return "Invalid memory action."

class YahooFinanceTool(BaseTool):
    name: str = "YahooFinanceTool"
    description: str = "Fetches real-time stock data from Yahoo Finance (prices in USD)."

    def _run(self, ticker: str, ma_period: int = 50) -> str:
        try:
            stock = yf.Ticker(ticker)
            current_price = stock.history(period="1d")["Close"].iloc[-1]
            history_5d = stock.history(period="5d")["Close"]
            trend = "up" if history_5d.iloc[-1] > history_5d.iloc[0] else "down" if history_5d.iloc[-1] < history_5d.iloc[0] else "stable"
            volatility = history_5d.std()
            risk = "Low" if volatility < 5 else "Medium" if volatility < 15 else "High"
            company_name = stock.info.get("longName", ticker)
            return json.dumps({
                "ticker": ticker,
                "company": company_name,
                "price": round(current_price, 2),
                "trend": trend,
                "volatility": round(volatility, 2),
                "risk": risk
            })
        except Exception as e:
            return f"Error fetching data for {ticker}: {str(e)}"

class DatabaseTool(BaseTool):
    name: str = "DatabaseTool"
    description: str = "Manages portfolio, watchlist, purchases, alerts, price history, preferences, and notifications in SQLite."

    def _run(self, action: str, **kwargs) -> Optional[str]:
        db_conn = sqlite3.connect(db_path)
        c = db_conn.cursor()
        try:
            if action == "add_to_portfolio":
                c.execute("INSERT OR REPLACE INTO portfolio (ticker, company) VALUES (?, ?)", (kwargs["ticker"], kwargs["company"]))
                self.log_notification(f"Added {kwargs['company']} ({kwargs['ticker']}) to portfolio")
            elif action == "get_portfolio":
                c.execute("SELECT ticker, company FROM portfolio")
                return json.dumps(c.fetchall())
            elif action == "add_to_watchlist":
                c.execute("INSERT OR REPLACE INTO watchlist (ticker, company) VALUES (?, ?)", (kwargs["ticker"], kwargs["company"]))
                self.log_notification(f"Added {kwargs['company']} ({kwargs['ticker']}) to watchlist")
            elif action == "get_watchlist":
                c.execute("SELECT ticker, company FROM watchlist")
                return json.dumps(c.fetchall())
            elif action == "add_purchase":
                c.execute("INSERT OR REPLACE INTO purchases (ticker, company, purchase_price, quantity, currency) VALUES (?, ?, ?, ?, ?)",
                          (kwargs["ticker"], kwargs["company"], kwargs["purchase_price"], kwargs.get("quantity", 1), kwargs["currency"]))
                self.log_notification(f"Logged purchase of {kwargs.get('quantity', 1)} {kwargs['company']} ({kwargs['ticker']}) at {kwargs['currency']}{kwargs['purchase_price']}")
            elif action == "get_purchases":
                c.execute("SELECT ticker, company, purchase_price, quantity, currency FROM purchases")
                return json.dumps(c.fetchall())
            elif action == "log_price":
                date = datetime.now().strftime("%Y-%m-%d")
                c.execute("INSERT OR REPLACE INTO price_history (ticker, date, price, currency) VALUES (?, ?, ?, ?)",
                          (kwargs["ticker"], date, kwargs["price"], kwargs["currency"]))
            elif action == "get_price_history":
                c.execute("SELECT date, price, currency FROM price_history WHERE ticker = ? ORDER BY date", (kwargs["ticker"],))
                return json.dumps(c.fetchall())
            elif action == "add_alert":
                c.execute("INSERT OR REPLACE INTO alerts (ticker, target_price, currency) VALUES (?, ?, ?)",
                          (kwargs["ticker"], kwargs["target_price"], kwargs["currency"]))
                self.log_notification(f"Set alert for {kwargs['ticker']} at {kwargs['currency']}{kwargs['target_price']}")
            elif action == "get_alerts":
                c.execute("SELECT ticker, target_price, currency FROM alerts")
                return json.dumps(c.fetchall())
            elif action == "get_purchases_for_alerts":
                c.execute("SELECT ticker, purchase_price, quantity, currency FROM purchases")
                return json.dumps(c.fetchall())
            elif action == "set_preference":
                c.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (kwargs["key"], kwargs["value"]))
            elif action == "get_preference":
                c.execute("SELECT value FROM preferences WHERE key = ?", (kwargs["key"],))
                result = c.fetchone()
                return result[0] if result else kwargs.get("default", "USD")
            elif action == "log_notification":
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO notifications (message, timestamp) VALUES (?, ?)", (kwargs["message"], timestamp))
            elif action == "get_notifications":
                c.execute("SELECT message, timestamp FROM notifications ORDER BY timestamp DESC LIMIT 5")
                return json.dumps(c.fetchall())
            db_conn.commit()
        except Exception as e:
            return f"Database error: {str(e)}"
        finally:
            db_conn.close()
        return "Success" if "get" not in action else None

    def log_notification(self, message):
        self._run("log_notification", message=message)

# Alert Checker
class AlertChecker:
    def __init__(self, db_tool, yahoo_tool):
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool
        self.alerts = []
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._check_alerts_loop)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _check_alerts_loop(self):
        while self.running:
            user_currency = self.db_tool._run("get_preference", key="currency", default="USD")
            user_currency = user_currency if user_currency in EXCHANGE_RATES else "USD"
            rate_to_usd = EXCHANGE_RATES[user_currency]
            alerts = json.loads(self.db_tool._run("get_alerts") or "[]")
            purchases = json.loads(self.db_tool._run("get_purchases_for_alerts") or "[]")
            triggered = []
            for ticker, target_price, alert_currency in alerts:
                data = json.loads(self.yahoo_tool._run(ticker))
                if "price" in data:
                    usd_price = data["price"]
                    alert_price_in_usd = target_price / EXCHANGE_RATES.get(alert_currency, 1.0)
                    if usd_price >= alert_price_in_usd:
                        converted_price = usd_price * EXCHANGE_RATES[user_currency]
                        triggered.append(f"Alert: {data['company']} ({ticker}) is at {user_currency}{converted_price:.2f}, hit your target of {alert_currency}{target_price}")
                        self.db_tool._run("log_notification", message=f"Alert triggered for {ticker} at {user_currency}{converted_price:.2f}")
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
                        triggered.append(f"Reminder: {data['company']} ({ticker}) bought at {purchase_currency}{purchase_price} is now {user_currency}{converted_price:.2f}. Selling yields profit of {user_currency}{converted_profit:.2f} (≥ {user_currency}{min_profit}).")
                        self.db_tool._run("log_notification", message=f"Profit reminder for {ticker}: {user_currency}{converted_profit:.2f}")
            self.alerts = triggered
            time.sleep(10)

    def get_alerts(self):
        return self.alerts


config = dict(
    llm=dict(
        provider="openai",
        config=dict(
            model=get_model_from_database().name,
            api_key=get_model_from_database().api_key,
            base_url=get_model_from_database().url
        ),
    ),
    embedder=dict(
        provider="huggingface",
        config=dict(
            model="multi-qa-MiniLM-L6-cos-v1"
        )
    ),
vector_store= dict(
                provider="chroma",
                config=dict(
                    collection_name="memory",
                    path=f"{os.path.join(SESSION_PATH, 'general-rag')}",
                    )
                )
)
# Available Tools
available_tools = {
    "SecureContactManager": SecureContactManagerTool(),
    "EncryptDataTool": EncryptDataTool(),
    "APICallTool": APICallTool(),
    "TaskTrackerTool": TaskTrackerTool(),
    "MemoryManagerTool": MemoryManagerTool(),
    "YahooFinanceTool": YahooFinanceTool(),
    "DatabaseTool": DatabaseTool(),
    "WebsiteSearchTool": WebsiteSearchTool(config=config),
    "FileReadTool": FileReadTool(),
    "ScrapeWebsiteTool": ScrapeWebsiteTool(),
    "DirectoryReadTool": DirectoryReadTool(),
    "SerperDevTool": SerperDevTool() if os.environ.get("SERPER_API_KEY") else None,
    "TXTSearchTool":  TXTSearchTool(config=config),
    "EXASearchTool": EXASearchTool(),
    "CodeDocsSearchTool": CodeDocsSearchTool(config=config),
    "CodeInterpreterTool": CodeInterpreterTool(),
    "CSVSearchTool": CSVSearchTool(config=config),
    "DOCXSearchTool": DOCXSearchTool(config=config),
    "DirectorySearchTool": DirectorySearchTool(config=config),
    "JSONSearchTool": JSONSearchTool(config=config),
    "MDXSearchTool": MDXSearchTool(config=config),
    "PDFSearchTool": PDFSearchTool(config=config),
    "ScrapeElementFromWebsiteTool": ScrapeElementFromWebsiteTool(),
    "SeleniumScrapingTool": SeleniumScrapingTool(),
    "XMLSearchTool": XMLSearchTool(config=config),
    "YoutubeChannelSearchTool": YoutubeChannelSearchTool(config=config),
    "YoutubeVideoSearchTool": YoutubeVideoSearchTool(config=config)
}
available_tools = {k: v for k, v in available_tools.items() if v is not None}

# Mode Decision Prompt
mode_decision_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""Analyze the query and context to determine the best mode:
    - Standard: For simple, direct questions or calculations (e.g., math, basic facts).
    - DeepSearch: For queries needing external, up-to-date, or broad information (e.g., news, trends, research).
    - Think: For queries requiring reasoning, planning, or subjective analysis (e.g., advice, strategies).
    Return only the mode name: Standard, DeepSearch, or Think."""),
    HumanMessage(content="Query: {input}\nContext: {context}")
])

# Agents
general_assistant = Agent(
    role='General Personal Assistant',
    goal='Provide comprehensive assistance combining executive support, stock market expertise, and general-purpose query handling with memory and mode-based processing',
    backstory="""You are an elite AI assistant created by xAI, designed to handle a wide range of tasks from scheduling and stock management to in-depth research and reasoning. You use a hybrid memory system (Mem0 and SQLite) to personalize responses and dynamically select the best mode (Standard, DeepSearch, Think) for each query. You support stock price tracking in user-preferred currencies (USD, INR, EUR, GBP) and manage secure contacts, tasks, and files.""",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=list(available_tools.values())
)

manager_agent = Agent(
    role='Task Manager',
    goal='Optimize task assignment with minimal LLM requests using memory and caching',
    backstory="""You are an AI manager created by xAI, designed to reduce LLM usage with smart task delegation and mode selection.""",
    verbose=True,
    allow_delegation=True,
    llm=llm
)

# Task Definitions
def create_schedule_task(user_input):
    return Task(
        description=f"Create a detailed schedule: {user_input}.",
        agent=general_assistant,
        expected_output="Comprehensive schedule with time blocks, locations, attendees, and priorities",
        tools=[available_tools["SecureContactManager"], available_tools["MemoryManagerTool"]]
    )

def prepare_briefing_task(topic):
    return Task(
        description=f"Prepare a briefing on: {topic}.",
        agent=general_assistant,
        expected_output="Concise briefing with key points, data, and recommendations",
        tools=[available_tools["WebsiteSearchTool"], available_tools["MemoryManagerTool"]]
    )

def draft_communication_task(details):
    return Task(
        description=f"Draft a formal communication: {details}.",
        agent=general_assistant,
        expected_output="Polished, professional communication draft",
        tools=[available_tools["FileReadTool"], available_tools["MemoryManagerTool"]]
    )

def crisis_management_task(situation):
    return Task(
        description=f"Develop a crisis plan for: {situation}.",
        agent=general_assistant,
        expected_output="Crisis response plan with actions, contacts, and communication outline",
        tools=[available_tools["SecureContactManager"], available_tools["APICallTool"], available_tools["MemoryManagerTool"]]
    )

def handle_confidential_file_task(file_path, action):
    return Task(
        description=f"Handle confidential file at: {file_path}, action: {action}.",
        agent=general_assistant,
        expected_output="Summary of file contents or secure storage confirmation",
        tools=[available_tools["FileReadTool"], available_tools["EncryptDataTool"], available_tools["MemoryManagerTool"]]
    )

def stakeholder_update_task(stakeholder_info):
    return Task(
        description=f"Prepare stakeholder update: {stakeholder_info}.",
        agent=general_assistant,
        expected_output="Tailored stakeholder update",
        tools=[available_tools["SecureContactManager"], available_tools["MemoryManagerTool"]]
    )

def manage_contact_task(action,name,role,contact_info):
    return Task(
    description=f"Manage contacts: Action: {action}, Name: {name}, Role: {role}, Info: {contact_info}.",
    agent=general_assistant,
    expected_output="Result of contact management action",
    tools=[available_tools["SecureContactManager"], available_tools["MemoryManagerTool"]]
)

def prepare_meeting_task(meeting_details):
    return Task(
        description=f"Prepare meeting: {meeting_details}.",
        agent=general_assistant,
        expected_output="Meeting agenda with attendees and background information",
        tools=[available_tools["SecureContactManager"], available_tools["FileReadTool"], available_tools["MemoryManagerTool"]]
)

def review_history_task():
    return Task(
        description="Retrieve request history from database.",
        agent=general_assistant,
        expected_output="Sanitized list of previous requests with timestamps",
        tools=[available_tools["FileReadTool"], available_tools["MemoryManagerTool"]]
    )

def analyze_competitor_task(company):
    return Task(
        description=f"Analyze competitor: {company}.",
        agent=general_assistant,
        expected_output="Competitor analysis with market position, strengths, and weaknesses",
        tools=[available_tools["WebsiteSearchTool"], available_tools["APICallTool"], available_tools["MemoryManagerTool"]]
    )

def generate_report_task(data_file, format):
    return Task(
        description=f"Generate report from: {data_file} in {format}.",
        agent=general_assistant,
        expected_output=f"Formatted report in {format}",
        tools=[available_tools["FileReadTool"], available_tools["CSVSearchTool"], available_tools["MemoryManagerTool"]]
    )

def monitor_news_task(topic):
    return Task(
        description=f"Monitor news on: {topic}.",
        agent=general_assistant,
        expected_output="Summary of recent news and trends",
        tools=[available_tools["WebsiteSearchTool"], available_tools["MemoryManagerTool"]]
    )

def review_code_task(repo_url):
    return Task(
        description=f"Review code at: {repo_url}.",
        agent=general_assistant,
        expected_output="Code review with suggestions and findings",
        tools=[available_tools["CodeInterpreterTool"], available_tools["MemoryManagerTool"]]
    )

def fetch_external_data_task(api_url):
    return Task(
        description=f"Fetch data from external API: {api_url}.",
        agent=general_assistant,
        expected_output="Processed data from the API",
        tools=[available_tools["APICallTool"], available_tools["MemoryManagerTool"]]
    )

def track_task_status_task(task_id, status=None, result=None):
    return Task(
        description=f"Track task status: {task_id}, Status: {status}, Result: {result}.",
        agent=general_assistant,
        expected_output="Task status update or retrieval result",
        tools=[available_tools["TaskTrackerTool"], available_tools["MemoryManagerTool"]]
    )

def schedule_follow_up_task(contact_name, message):
    return Task(
        description=f"Schedule a follow-up with {contact_name}: {message}.",
        agent=general_assistant,
        expected_output="Confirmation of follow-up scheduling",
        tools=[available_tools["SecureContactManager"], available_tools["MemoryManagerTool"]]
    )

def check_stock_price_task(ticker):
    return Task(
        description=f"Check the current stock price for {ticker}.",
        agent=general_assistant,
        expected_output="Current stock price and trend in the user's preferred currency",
        tools=[available_tools["YahooFinanceTool"], available_tools["DatabaseTool"]]
    )

def set_currency_task(currency):
    return Task(
        description=f"Set the user's preferred currency to {currency}.",
        agent=general_assistant,
        expected_output=f"Confirmation that currency is set to {currency}",
        tools=[available_tools["DatabaseTool"]]
    )

def add_stock_purchase_task(ticker, purchase_price, currency, target_price=None, min_profit=None):
    return Task(
        description=f"Add a stock purchase for {ticker} at {currency}{purchase_price}, optionally set a profit reminder for target {currency}{target_price} with minimum profit {currency}{min_profit}.",
        agent=general_assistant,
        expected_output="Confirmation of purchase addition and optional reminder setup",
        tools=[available_tools["YahooFinanceTool"], available_tools["DatabaseTool"], available_tools["MemoryManagerTool"]]
    )

def monitor_stock_task(ticker):
    return Task(
        description=f"Monitor stock {ticker} for real-time updates (simulated).",
        agent=general_assistant,
        expected_output="Series of price updates for the stock in the user's currency",
        tools=[available_tools["YahooFinanceTool"], available_tools["DatabaseTool"]]
    )

def standard_mode_task(query, user_id):
    return Task(
        description=f"Handle query in Standard mode: {query}.",
        agent=general_assistant,
        expected_output="Direct, concise response to the query",
        tools=[available_tools["CalculatorTool"], available_tools["MemoryManagerTool"], available_tools["DatabaseTool"]]
    )

def deepsearch_mode_task(query, user_id):
    return Task(
        description=f"Handle query in DeepSearch mode: {query}. Perform iterative searches and synthesize results.",
        agent=general_assistant,
        expected_output="Comprehensive response with synthesized search results",
        tools=[ available_tools["WebsiteSearchTool"], available_tools["SerperDevTool"], available_tools["MemoryManagerTool"]]
    )

def think_mode_task(query, user_id):
    return Task(
        description=f"Handle query in Think mode: {query}. Reason step-by-step and provide a detailed explanation.",
        agent=general_assistant,
        expected_output="Detailed response with step-by-step reasoning",
        tools=[available_tools["MemoryManagerTool"], available_tools["DatabaseTool"], available_tools["CalculatorTool"]]
    )

task_functions = {
    name.replace("_task", ""): obj for name, obj in globals().items()
    if callable(obj) and name.endswith("_task") and name != "decide_task_task"
}

# Task Trie for Quick Matching
class TrieNode:
    def __init__(self):
        self.children = defaultdict(TrieNode)
        self.is_end = False
        self.task_name = None

class TaskTrie:
    def __init__(self):
        self.root = TrieNode()
        for task_name in task_functions.keys():
            node = self.root
            for char in task_name:
                node = node.children[char]
            node.is_end = True
            node.task_name = task_name

    def find_task(self, text):
        node = self.root
        for char in text.lower():
            if char not in node.children:
                return None
            node = node.children[char]
            if node.is_end:
                return node.task_name
        return None

task_trie = TaskTrie()

# Memory Management
def retrieve_context(query: str, user_id: str) -> str:
    memories = mem0.search_memory(query, limit=5)
    serialized_memories = ' '.join([mem["memory"] for mem in memories])
    return serialized_memories or ""

def decide_mode(query: str, user_id: str) -> str:
    from core.Agent_models import get_model
    context = retrieve_context(query, user_id)
    mode_chain = mode_decision_prompt | get_model()
    mode = mode_chain.invoke({"input": query, "context": context}).content.strip()
    return mode

# Task Decision
def decide_task_task(user_input, user_id):
    request_hash = hashlib.md5(user_input.encode()).hexdigest()
    cached_short = short_term_memory.get(f"decision_{request_hash}")
    if cached_short:
        return Task(
            description="Cached decision from short-term memory",
            agent=manager_agent,
            expected_output=cached_short
        )
    cursor.execute("SELECT response FROM cache WHERE request_hash = ?", (request_hash,))
    cached_long = cursor.fetchone()
    if cached_long:
        short_term_memory.add(f"decision_{request_hash}", cached_long[0])
        return Task(
            description="Cached decision from long-term memory",
            agent=manager_agent,
            expected_output=cached_long[0]
        )
    task_list = ", ".join(task_functions.keys())
    return Task(
        description=f"Analyze input: '{user_input}'. Select task from: {task_list}. Extract params, return: {{'task': 'name', 'params': {{'key': 'value'}}}}. Default to 'prepare_briefing' if unsure.",
        agent=manager_agent,
        expected_output="JSON-like string with task and parameters",
        callback=lambda result: (
            short_term_memory.add(f"decision_{request_hash}", str(result)),
            cursor.execute("INSERT OR REPLACE INTO cache (request_hash, response) VALUES (?, ?)",
                           (request_hash, str(result)))
        )
    )

# Crew Setup
assistant_crew = Crew(
    agents=[manager_agent, general_assistant],
    tasks=[],
    verbose=True
)



# Main Process Request
def process_request(user_input: str):
    from config import SessionManager
    from jarvis_integration.models.users import Users
    s=SessionManager()
    s.load_session()
    user=Users.get_user_by_email(s.get_email())
    user_id=user.id
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    request_hash = hashlib.md5(user_input.encode()).hexdigest()

    # Check cache
    cached_short = short_term_memory.get(f"response_{request_hash}")
    if cached_short:
        return cached_short
    cursor.execute("SELECT response FROM request_history WHERE request = ? ORDER BY id DESC LIMIT 1", (user_input,))
    cached_long = cursor.fetchone()
    if cached_long and cached_long[0]:
        short_term_memory.add(f"response_{request_hash}", cached_long[0])
        return cached_long[0]

    # Quick task match
    quick_task = task_trie.find_task(user_input)
    if quick_task and quick_task not in ["prepare_briefing", "standard_mode", "deepsearch_mode", "think_mode"]:
        params = {"user_input": user_input} if "user_input" in inspect.signature(task_functions[quick_task]).parameters else {}
        decision = json.dumps({"task": quick_task, "params": params})
    else:
        # Decide mode for general queries
        mode = decide_mode(user_input, user_id)
        if mode == "Standard":
            decision = json.dumps({"task": "standard_mode", "params": {"query": user_input, "user_id": user_id}})
        elif mode == "DeepSearch":
            decision = json.dumps({"task": "deepsearch_mode", "params": {"query": user_input, "user_id": user_id}})
        elif mode == "Think":
            decision = json.dumps({"task": "think_mode", "params": {"query": user_input, "user_id": user_id}})
        else:
            assistant_crew.tasks = [decide_task_task(user_input, user_id)]
            decision = assistant_crew.kickoff()

    try:
        decision_dict = json.loads(decision.replace("'", "\""))
        task_name = decision_dict["task"]
        params = decision_dict["params"]
    except Exception as e:
        task_name = "prepare_briefing"
        params = {"topic": user_input}

    task_func = task_functions.get(task_name, prepare_briefing_task)
    signature = inspect.signature(task_func)
    task_params = {param: params.get(param, user_input if param == "user_input" else None)
                   for param in signature.parameters}
    task = task_func(**{k: v for k, v in task_params.items() if v is not None})

    # Handle special cases
    if task_name == "handle_confidential_file" and params.get("action") == "store":
        cursor.execute("INSERT OR REPLACE INTO confidential_notes (file_path, note) VALUES (?, ?)",
                       (params.get("file_path", "unknown.txt"), f"Stored at {timestamp}"))
        cursor.execute("INSERT OR REPLACE INTO long_term_memory (key, value, timestamp) VALUES (?, ?, ?)",
                       (f"confidential_{params.get('file_path', 'unknown.txt')}", "Stored", timestamp))
        available_tools["MemoryManagerTool"]._run("store_mem0", key=user_input, value="Stored confidential file", user_id=user_id)

    if task_name == "review_history":
        cursor.execute("SELECT timestamp, request FROM request_history")
        history = cursor.fetchall()
        task.expected_output = "\n".join([f"{ts}: {req}" for ts, req in history])

    # Execute task
    assistant_crew.tasks = [task]
    result = assistant_crew.kickoff()

    # Store results
    short_term_memory.add(f"response_{request_hash}", str(result))
    cursor.execute("INSERT INTO request_history (timestamp, request, response) VALUES (?, ?, ?)",
                   (timestamp, user_input, str(result)))
    cursor.execute("INSERT OR REPLACE INTO long_term_memory (key, value, timestamp) VALUES (?, ?, ?)",
                   (f"task_{task_name}_{request_hash}", str(result), timestamp))
    available_tools["MemoryManagerTool"]._run("store_mem0", key=user_input, value=str(result), user_id=user_id)

    if task_name in ["create_schedule", "draft_communication", "crisis_management"]:
        task_id = request_hash
        cursor.execute("INSERT OR REPLACE INTO tasks_status (task_id, status, result) VALUES (?, ?, ?)",
                       (task_id, "completed", str(result)))

    conn.commit()
    return result

# Example Usage
def main():
    print("General Personal Assistant: How can I assist you? (Type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            conn.close()
            print("Agent: Goodbye!")
            break
        response = process_request(user_input)
        print(f"Agent: {response}")

if __name__ == "__main__":
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    main()