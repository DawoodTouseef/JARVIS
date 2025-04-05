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
import os
import json
import sqlite3
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QLineEdit, QFormLayout, QComboBox, QTabWidget,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem

)
from PyQt5.QtGui import QFont
from config import  JARVIS_DIR
from langchain.tools import BaseTool
from typing import List, Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool


# SQLite Database Setup
conn = sqlite3.connect(os.path.join(JARVIS_DIR, "data", "assistant_data.db"), check_same_thread=False)
cursor = conn.cursor()

# Database tables
cursor.execute('''CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    role TEXT,
    goal TEXT,
    backstory TEXT,
    llm_id INTEGER,
    tools TEXT,
    FOREIGN KEY (llm_id) REFERENCES llms(id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    description TEXT,
    expected_output TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS llms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT,
    api_key TEXT,
    base_url TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT,
    code TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS crews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    agents TEXT,
    tasks TEXT
)''')
conn.commit()

TOOLS: List[BaseTool] = []
CREWS: List[Crew] = []


def load_integrations():
    """Load integrations from database."""
    cursor.execute("SELECT name, description FROM tools")
    tools_data = {row[0]: {"description": row[1]} for row in cursor.fetchall()}
    return tools_data


def save_tool_to_db(name: str, description: str, code: str):
    """Save tool details to the database."""
    cursor.execute("INSERT OR REPLACE INTO tools (name, description, code) VALUES (?, ?, ?)",
                   (name, description, code))
    conn.commit()


def save_agent_to_db(name: str, role: str, goal: str, backstory: str, llm_id: int, tools: str):
    """Save agent details to the database."""
    cursor.execute(
        "INSERT OR REPLACE INTO agents (name, role, goal, backstory, llm_id, tools) VALUES (?, ?, ?, ?, ?, ?)",
        (name, role, goal, backstory, llm_id, tools))
    conn.commit()
    return cursor.lastrowid


def save_task_to_db(agent_id: int, description: str, expected_output: str):
    """Save task details to the database."""
    cursor.execute("INSERT INTO tasks (agent_id, description, expected_output) VALUES (?, ?, ?)",
                   (agent_id, description, expected_output))
    conn.commit()


def save_llm_to_db(model: str, api_key: str, base_url: str):
    """Save LLM details to the database."""
    cursor.execute("INSERT INTO llms (model, api_key, base_url) VALUES (?, ?, ?)",
                   (model, api_key, base_url))
    conn.commit()
    return cursor.lastrowid


def save_crew_to_db(name: str, agents: List[str], tasks: List[str]):
    """Save crew details to the database."""
    cursor.execute("INSERT OR REPLACE INTO crews (name, agents, tasks) VALUES (?, ?, ?)",
                   (name, json.dumps(agents), json.dumps(tasks)))
    conn.commit()


def delete_agent_from_db(name: str):
    """Delete agent from database."""
    cursor.execute("DELETE FROM agents WHERE name = ?", (name,))
    cursor.execute("DELETE FROM tasks WHERE agent_id IN (SELECT id FROM agents WHERE name = ?)", (name,))
    conn.commit()

def delete_task_from_db(description: str):
    """Delete task from database."""
    cursor.execute("DELETE FROM tasks WHERE description = ?", (description,))
    conn.commit()

def delete_llm_from_db(model: str):
    """Delete LLM from database."""
    # First check if any agents are using this LLM
    cursor.execute("SELECT COUNT(*) FROM agents WHERE llm_id IN (SELECT id FROM llms WHERE model = ?)", (model,))
    if cursor.fetchone()[0] > 0:
        raise ValueError("Cannot delete LLM - it's being used by one or more agents")
    cursor.execute("DELETE FROM llms WHERE model = ?", (model,))
    conn.commit()

def delete_tool_from_db(name: str):
    """Delete tool from database."""
    # First check if any agents are using this tool
    cursor.execute("SELECT COUNT(*) FROM agents WHERE tools LIKE ?", (f'%{name}%',))
    if cursor.fetchone()[0] > 0:
        raise ValueError("Cannot delete tool - it's being used by one or more agents")
    cursor.execute("DELETE FROM tools WHERE name = ?", (name,))
    conn.commit()

def delete_crew_from_db(name: str):
    """Delete crew from database."""
    cursor.execute("DELETE FROM crews WHERE name = ?", (name,))
    conn.commit()

def convert_to_crewai_tool(file_path: str, tool_name: str) -> str:
    """Convert uploaded Python function to a crewai tool."""
    with open(file_path, 'r') as f:
        code = f.read()

    import re
    func_match = re.search(r'def\s+(\w+)\s*\(', code)
    if not func_match:
        raise ValueError("No function found in uploaded file")
    func_name = func_match.group(1)
    path=os.path.join(JARVIS_DIR,"components",func_name)
    if not os.path.exists(path):
        os.makedirs(path,exist_ok=True)
    with open(os.path.join(JARVIS_DIR,"components",func_name,f"{func_name}.py"),"w") as f:
        f.write(code)
    return code


def load_tool_from_db(tool_name: str) -> Optional[BaseTool]:
    """Load tool from database and instantiate it."""
    try:
        # Get tool code from database
        cursor.execute("SELECT code FROM tools WHERE name = ?", (tool_name,))
        result = cursor.fetchone()
        if not result:
            print(f"Tool '{tool_name}' not found in database")
            return None

        code = result[0]

        # Execute the code
        locals_dict = {}

        # Execute the code to define the function
        exec(code, globals(), locals_dict)
        import re
        func_match = re.search(r'def\s+(\w+)\s*\(', code)
        if not func_match:
            raise ValueError("No function found in uploaded file")
        func_name = func_match.group(1)
        tools_function=tool(locals_dict[func_name])
        return tools_function

    except Exception as e:
        print(f"Error loading tool '{tool_name}': {str(e)}")
        return None


def get_llm_models():
    """Get list of available LLM models from database"""
    cursor.execute("SELECT model FROM llms")
    return [row[0] for row in cursor.fetchall()]


def get_agents():
    """Get list of available agents from database"""
    cursor.execute("SELECT name FROM agents")
    return [row[0] for row in cursor.fetchall()]


def get_tasks():
    """Get list of available tasks from database"""
    cursor.execute("SELECT description FROM tasks")
    return [row[0] for row in cursor.fetchall()]


def get_crews():
    """Get list of available crews from database"""
    cursor.execute("SELECT name FROM crews")
    return [row[0] for row in cursor.fetchall()]


def get_llms_with_details():
    """Get list of available LLMs with all details from database"""
    cursor.execute("SELECT * FROM llms")
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_agents_with_details():
    """Get list of available agents with all details from database"""
    cursor.execute("SELECT * FROM agents")
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_tasks_with_details():
    """Get list of available tasks with all details from database"""
    cursor.execute("SELECT * FROM tasks")
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_tools_with_details():
    """Get list of available tools with all details from database"""
    cursor.execute("SELECT * FROM tools")
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_crews_with_details():
    """Get list of available crews with all details from database"""
    cursor.execute("SELECT * FROM crews")
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

class DeleteDialog(QDialog):
    def __init__(self, item_type: str, item_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Delete {item_type}")
        self.item_type = item_type
        self.item_name = item_name
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        message = QLabel(f"Are you sure you want to delete {self.item_type} '{self.item_name}'?")
        layout.addWidget(message)

        buttons_layout = QHBoxLayout()
        confirm_button = QPushButton("Delete")
        confirm_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(confirm_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)


class NewIntegrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Integration")
        self.setFixedSize(900, 700)
        self.init_ui()
        self.current_llm_id = None

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Tool Tab
        self.init_tool_tab()
        # Agent Tab
        self.init_agent_tab()
        # Task Tab
        self.init_task_tab()
        # LLM Tab
        self.init_llm_tab()
        # Crew Tab
        self.init_crew_tab()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def init_tool_tab(self):
        tool_tab = QWidget()
        tool_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.tool_name = QLineEdit()
        self.tool_desc = QLineEdit()
        self.tool_file_button = QPushButton("Upload Tool File")
        self.tool_file_button.clicked.connect(self.upload_tool_file)
        self.tool_file_label = QLabel("No file selected")
        self.tool_file_path = ""

        form_layout.addRow("Tool Name:", self.tool_name)
        form_layout.addRow("Description:", self.tool_desc)
        form_layout.addRow("Tool File:", self.tool_file_button)
        form_layout.addRow("", self.tool_file_label)

        tool_layout.addLayout(form_layout)

        save_tool_button = QPushButton("Save Tool")
        save_tool_button.clicked.connect(self.save_tool)
        tool_layout.addWidget(save_tool_button)

        tool_tab.setLayout(tool_layout)
        self.tabs.addTab(tool_tab, "Tool")

    def init_agent_tab(self):
        agent_tab = QWidget()
        agent_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.agent_name = QLineEdit()
        self.agent_role = QLineEdit()
        self.agent_goal = QLineEdit()
        self.agent_backstory = QLineEdit()

        # LLM model selection
        self.agent_llm_combo = QComboBox()
        self.update_llm_combo()

        # Tools selection
        self.agent_tools_combo = QComboBox()
        self.update_tools_combo()
        self.agent_tools_list = QListWidget()

        add_tool_button = QPushButton("Add Tool")
        add_tool_button.clicked.connect(self.add_tool_to_agent)

        form_layout.addRow("Agent Name:", self.agent_name)
        form_layout.addRow("Role:", self.agent_role)
        form_layout.addRow("Goal:", self.agent_goal)
        form_layout.addRow("Backstory:", self.agent_backstory)
        form_layout.addRow("LLM Model:", self.agent_llm_combo)
        form_layout.addRow("Available Tools:", self.agent_tools_combo)
        form_layout.addRow("", add_tool_button)
        form_layout.addRow("Selected Tools:", self.agent_tools_list)

        agent_layout.addLayout(form_layout)

        save_agent_button = QPushButton("Save Agent")
        save_agent_button.clicked.connect(self.save_agent)
        agent_layout.addWidget(save_agent_button)

        agent_tab.setLayout(agent_layout)
        self.tabs.addTab(agent_tab, "Agent")

    def init_task_tab(self):
        task_tab = QWidget()
        task_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.task_agent_combo = QComboBox()
        self.update_agent_combo()
        self.task_desc = QLineEdit()
        self.task_output = QLineEdit()

        form_layout.addRow("Agent:", self.task_agent_combo)
        form_layout.addRow("Description:", self.task_desc)
        form_layout.addRow("Expected Output:", self.task_output)

        task_layout.addLayout(form_layout)

        save_task_button = QPushButton("Save Task")
        save_task_button.clicked.connect(self.save_task)
        task_layout.addWidget(save_task_button)

        task_tab.setLayout(task_layout)
        self.tabs.addTab(task_tab, "Task")

    def init_llm_tab(self):
        llm_tab = QWidget()
        llm_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.llm_model = QLineEdit()
        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.Password)
        self.llm_base_url = QLineEdit()

        form_layout.addRow("Model:", self.llm_model)
        form_layout.addRow("API Key:", self.llm_api_key)
        form_layout.addRow("Base URL:", self.llm_base_url)

        llm_layout.addLayout(form_layout)

        save_llm_button = QPushButton("Save LLM")
        save_llm_button.clicked.connect(self.save_llm)
        llm_layout.addWidget(save_llm_button)

        llm_tab.setLayout(llm_layout)
        self.tabs.addTab(llm_tab, "LLM")

    def init_crew_tab(self):
        crew_tab = QWidget()
        crew_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.crew_name = QLineEdit()

        # Available agents list
        self.available_agents_list = QListWidget()
        self.update_available_agents()

        # Selected agents list
        self.selected_agents_list = QListWidget()

        add_agent_button = QPushButton("Add Agent to Crew")
        add_agent_button.clicked.connect(self.add_agent_to_crew)

        remove_agent_button = QPushButton("Remove Agent from Crew")
        remove_agent_button.clicked.connect(self.remove_agent_from_crew)

        # Available tasks list
        self.available_tasks_list = QListWidget()
        self.update_available_tasks()

        # Selected tasks list
        self.selected_tasks_list = QListWidget()

        add_task_button = QPushButton("Add Task to Crew")
        add_task_button.clicked.connect(self.add_task_to_crew)

        remove_task_button = QPushButton("Remove Task from Crew")
        remove_task_button.clicked.connect(self.remove_task_from_crew)

        form_layout.addRow("Crew Name:", self.crew_name)
        form_layout.addRow("Available Agents:", self.available_agents_list)
        form_layout.addRow("", add_agent_button)
        form_layout.addRow("Selected Agents:", self.selected_agents_list)
        form_layout.addRow("", remove_agent_button)
        form_layout.addRow("Available Tasks:", self.available_tasks_list)
        form_layout.addRow("", add_task_button)
        form_layout.addRow("Selected Tasks:", self.selected_tasks_list)
        form_layout.addRow("", remove_task_button)

        crew_layout.addLayout(form_layout)

        save_crew_button = QPushButton("Save Crew")
        save_crew_button.clicked.connect(self.save_crew)
        crew_layout.addWidget(save_crew_button)

        crew_tab.setLayout(crew_layout)
        self.tabs.addTab(crew_tab, "Crew")

    def update_llm_combo(self):
        self.agent_llm_combo.clear()
        models = get_llm_models()
        self.agent_llm_combo.addItems(models or ["No LLMs available"])

    def update_tools_combo(self):
        self.agent_tools_combo.clear()
        cursor.execute("SELECT name FROM tools")
        tools = [row[0] for row in cursor.fetchall()]
        self.agent_tools_combo.addItems(tools or ["No tools available"])

    def update_agent_combo(self):
        self.task_agent_combo.clear()
        agents = get_agents()
        self.task_agent_combo.addItems(agents or ["No agents available"])

    def update_available_agents(self):
        self.available_agents_list.clear()
        agents = get_agents()
        for agent in agents:
            item = QListWidgetItem(agent)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.available_agents_list.addItem(item)

    def update_available_tasks(self):
        self.available_tasks_list.clear()
        tasks = get_tasks()
        for task in tasks:
            item = QListWidgetItem(task)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.available_tasks_list.addItem(item)

    def upload_tool_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Tool File", "", "Python Files (*.py)")
        if file_path:
            self.tool_file_path = file_path
            self.tool_file_label.setText(os.path.basename(file_path))
        else:
            self.tool_file_label.setText("No file selected")
            self.tool_file_path = ""

    def add_tool_to_agent(self):
        tool_name = self.agent_tools_combo.currentText()
        if tool_name and tool_name != "No tools available":
            self.agent_tools_list.addItem(tool_name)

    def add_agent_to_crew(self):
        selected_items = [self.available_agents_list.item(i) for i in range(self.available_agents_list.count())
                          if self.available_agents_list.item(i).checkState() == Qt.Checked]
        for item in selected_items:
            if not any(self.selected_agents_list.item(i).text() == item.text()
                       for i in range(self.selected_agents_list.count())):
                self.selected_agents_list.addItem(item.text())

    def remove_agent_from_crew(self):
        selected_items = self.selected_agents_list.selectedItems()
        for item in selected_items:
            self.selected_agents_list.takeItem(self.selected_agents_list.row(item))

    def add_task_to_crew(self):
        selected_items = [self.available_tasks_list.item(i) for i in range(self.available_tasks_list.count())
                          if self.available_tasks_list.item(i).checkState() == Qt.Checked]
        for item in selected_items:
            if not any(self.selected_tasks_list.item(i).text() == item.text()
                       for i in range(self.selected_tasks_list.count())):
                self.selected_tasks_list.addItem(item.text())

    def remove_task_from_crew(self):
        selected_items = self.selected_tasks_list.selectedItems()
        for item in selected_items:
            self.selected_tasks_list.takeItem(self.selected_tasks_list.row(item))

    def save_tool(self):
        tool_name = self.tool_name.text().strip()
        tool_desc = self.tool_desc.text().strip()

        if not tool_name or not tool_desc or not self.tool_file_path:
            QMessageBox.warning(self, "Error", "All tool fields are required")
            return

        try:
            tool_code = convert_to_crewai_tool(self.tool_file_path, tool_name)
            save_tool_to_db(tool_name, tool_desc, tool_code)
            QMessageBox.information(self, "Success", "Tool saved successfully")
            self.update_tools_combo()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save tool: {str(e)}")

    def save_agent(self):
        agent_name = self.agent_name.text().strip()
        agent_role = self.agent_role.text().strip()
        agent_goal = self.agent_goal.text().strip()
        agent_backstory = self.agent_backstory.text().strip()
        llm_model = self.agent_llm_combo.currentText()

        if not agent_name or not agent_role or not agent_goal or not agent_backstory:
            QMessageBox.warning(self, "Error", "All agent fields except tools are required")
            return

        # Get LLM ID
        cursor.execute("SELECT id FROM llms WHERE model = ?", (llm_model,))
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(self, "Error", "Selected LLM model not found")
            return
        llm_id = result[0]

        # Get selected tools
        tools = []
        for i in range(self.agent_tools_list.count()):
            tools.append(self.agent_tools_list.item(i).text())
        tools_str = ",".join(tools) if tools else ""

        try:
            save_agent_to_db(agent_name, agent_role, agent_goal, agent_backstory, llm_id, tools_str)
            QMessageBox.information(self, "Success", "Agent saved successfully")
            self.update_agent_combo()
            self.update_available_agents()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save agent: {str(e)}")

    def save_task(self):
        agent_name = self.task_agent_combo.currentText()
        task_desc = self.task_desc.text().strip()
        task_output = self.task_output.text().strip()

        if not agent_name or agent_name == "No agents available":
            QMessageBox.warning(self, "Error", "No agent selected")
            return

        if not task_desc or not task_output:
            QMessageBox.warning(self, "Error", "All task fields are required")
            return

        # Get agent ID
        cursor.execute("SELECT id FROM agents WHERE name = ?", (agent_name,))
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(self, "Error", "Selected agent not found")
            return
        agent_id = result[0]

        try:
            save_task_to_db(agent_id, task_desc, task_output)
            QMessageBox.information(self, "Success", "Task saved successfully")
            self.update_available_tasks()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save task: {str(e)}")

    def save_llm(self):
        model = self.llm_model.text().strip()
        api_key = self.llm_api_key.text().strip()
        base_url = self.llm_base_url.text().strip()

        if not model or not api_key or not base_url:
            QMessageBox.warning(self, "Error", "All LLM fields are required")
            return

        try:
            save_llm_to_db(model, api_key, base_url)
            QMessageBox.information(self, "Success", "LLM saved successfully")
            self.update_llm_combo()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save LLM: {str(e)}")

    def save_crew(self):
        crew_name = self.crew_name.text().strip()

        if not crew_name:
            QMessageBox.warning(self, "Error", "Crew name is required")
            return

        # Get selected agents
        agents = []
        for i in range(self.selected_agents_list.count()):
            agents.append(self.selected_agents_list.item(i).text())

        # Get selected tasks
        tasks = []
        for i in range(self.selected_tasks_list.count()):
            tasks.append(self.selected_tasks_list.item(i).text())

        if not agents or not tasks:
            QMessageBox.warning(self, "Error", "Crew must have at least one agent and one task")
            return

        try:
            save_crew_to_db(crew_name, agents, tasks)
            QMessageBox.information(self, "Success", "Crew saved successfully")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save crew: {str(e)}")


class CrewItem(QWidget):
    def __init__(self, crew_name, parent=None):
        super().__init__(parent)
        self.crew_name = crew_name
        self.connected = self.check_connection()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        name_label = QLabel(self.crew_name)
        name_label.setFont(QFont("Arial", 14))
        layout.addWidget(name_label)
        layout.addStretch()

        self.connect_button = QPushButton("Disconnect" if self.connected else "Connect")
        self.connect_button.setStyleSheet(
            "background-color: #03a9f4; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_crew)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def check_connection(self):
        return any(crew.name == self.crew_name for crew in CREWS)

    def toggle_connection(self):
        if self.connected:
            self.disconnect_crew()
        else:
            self.connect_crew()

    def connect_crew(self):
        cursor.execute("SELECT agents, tasks FROM crews WHERE name = ?", (self.crew_name,))
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(self, "Error", "Crew not found")
            return

        agents_json, tasks_json = result
        agents = json.loads(agents_json)
        tasks = json.loads(tasks_json)

        # Create crew
        crew = Crew(
            agents=[self.get_agent_by_name(name) for name in agents],
            tasks=[self.get_task_by_description(desc) for desc in tasks]
        )

        CREWS.append(crew)
        self.connected = True
        self.connect_button.setText("Disconnect")
        print(f"Connected crew: {self.crew_name}")

    def disconnect_crew(self):
        global CREWS
        CREWS = [crew for crew in CREWS if crew.name != self.crew_name]
        self.connected = False
        self.connect_button.setText("Connect")
        print(f"Disconnected crew: {self.crew_name}")

    def delete_crew(self):
        if self.connected:
            self.disconnect_crew()

        dialog = DeleteDialog("crew", self.crew_name, self)
        if dialog.exec_() == QDialog.Accepted:
            delete_crew_from_db(self.crew_name)
            self.setParent(None)
            self.deleteLater()
            print(f"Deleted crew: {self.crew_name}")

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        cursor.execute("SELECT role, goal, backstory, llm_id, tools FROM agents WHERE name = ?", (name,))
        result = cursor.fetchone()
        if not result:
            return None

        role, goal, backstory, llm_id, tools_str = result

        # Get LLM details
        cursor.execute("SELECT model, api_key, base_url FROM llms WHERE id = ?", (llm_id,))
        llm_result = cursor.fetchone()
        if not llm_result:
            return None

        model, api_key, base_url = llm_result
        llm = {"model": model, "api_key": api_key, "base_url": base_url}

        # Get tools
        tools = []
        if tools_str:
            for tool_name in tools_str.split(","):
                tool = load_tool_from_db(tool_name.strip())
                if tool:
                    tools.append(tool)

        return Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            tools=tools,
            verbose=True
        )

    def get_task_by_description(self, description: str) -> Optional[Task]:
        cursor.execute("SELECT agent_id, expected_output FROM tasks WHERE description = ?", (description,))
        result = cursor.fetchone()
        if not result:
            return None

        agent_id, expected_output = result

        # Get agent name
        cursor.execute("SELECT name FROM agents WHERE id = ?", (agent_id,))
        agent_result = cursor.fetchone()
        if not agent_result:
            return None

        agent_name = agent_result[0]
        agent = self.get_agent_by_name(agent_name)
        if not agent:
            return None

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agent
        )


class AgentItem(QWidget):
    def __init__(self, agent_data, parent=None):
        super().__init__(parent)
        self.agent_data = agent_data
        self.connected = self.check_connection()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # Main info
        info_layout = QVBoxLayout()
        name_label = QLabel(self.agent_data['name'])
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        role_label = QLabel(f"Role: {self.agent_data['role']}")
        info_layout.addWidget(name_label)
        info_layout.addWidget(role_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.connect_button = QPushButton("Disconnect" if self.connected else "Connect")
        self.connect_button.setStyleSheet(
            "background-color: #03a9f4; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.connect_button.clicked.connect(self.toggle_connection)
        button_layout.addWidget(self.connect_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_agent)
        button_layout.addWidget(self.delete_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.edit_button.clicked.connect(self.edit_agent)
        button_layout.addWidget(self.edit_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def check_connection(self):
        return any(agent.name == self.agent_data['name'] for agent in [crew.agents for crew in CREWS])

    def toggle_connection(self):
        # Connection is managed through crews, so this might just show status
        self.connected = not self.connected
        self.connect_button.setText("Disconnect" if self.connected else "Connect")

    def delete_agent(self):
        dialog = DeleteDialog("agent", self.agent_data['name'], self)
        if dialog.exec_() == QDialog.Accepted:
            delete_agent_from_db(self.agent_data['name'])
            self.setParent(None)
            self.deleteLater()

    def edit_agent(self):
        dialog = NewIntegrationDialog(self)
        dialog.tabs.setCurrentIndex(1)  # Switch to Agent tab
        # Pre-fill the form with agent data
        dialog.agent_name.setText(self.agent_data['name'])
        dialog.agent_role.setText(self.agent_data['role'])
        dialog.agent_goal.setText(self.agent_data['goal'])
        dialog.agent_backstory.setText(self.agent_data['backstory'])

        # Set LLM
        cursor.execute("SELECT model FROM llms WHERE id = ?", (self.agent_data['llm_id'],))
        llm_model = cursor.fetchone()[0]
        index = dialog.agent_llm_combo.findText(llm_model)
        if index >= 0:
            dialog.agent_llm_combo.setCurrentIndex(index)

        # Set tools
        if self.agent_data['tools']:
            for tool_name in self.agent_data['tools'].split(','):
                dialog.agent_tools_list.addItem(tool_name.strip())

        if dialog.exec_():
            # Refresh the parent widget if needed
            if self.parent() and hasattr(self.parent(), 'refresh'):
                self.parent().refresh()


class TaskItem(QWidget):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # Main info
        info_layout = QVBoxLayout()
        desc_label = QLabel(self.task_data['description'])
        desc_label.setFont(QFont("Arial", 12))
        output_label = QLabel(f"Expected: {self.task_data['expected_output']}")
        info_layout.addWidget(desc_label)
        info_layout.addWidget(output_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_task)
        button_layout.addWidget(self.delete_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.edit_button.clicked.connect(self.edit_task)
        button_layout.addWidget(self.edit_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def delete_task(self):
        dialog = DeleteDialog("task", self.task_data['description'], self)
        if dialog.exec_() == QDialog.Accepted:
            delete_task_from_db(self.task_data['description'])
            self.setParent(None)
            self.deleteLater()

    def edit_task(self):
        dialog = NewIntegrationDialog(self)
        dialog.tabs.setCurrentIndex(2)  # Switch to Task tab

        # Get agent name
        cursor.execute("SELECT name FROM agents WHERE id = ?", (self.task_data['agent_id'],))
        agent_name = cursor.fetchone()[0]

        # Pre-fill the form
        index = dialog.task_agent_combo.findText(agent_name)
        if index >= 0:
            dialog.task_agent_combo.setCurrentIndex(index)
        dialog.task_desc.setText(self.task_data['description'])
        dialog.task_output.setText(self.task_data['expected_output'])

        if dialog.exec_():
            if self.parent() and hasattr(self.parent(), 'refresh'):
                self.parent().refresh()


class ToolItem(QWidget):
    def __init__(self, tool_data, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # Main info
        info_layout = QVBoxLayout()
        name_label = QLabel(self.tool_data['name'])
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        desc_label = QLabel(self.tool_data['description'])
        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_tool)
        button_layout.addWidget(self.delete_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.edit_button.clicked.connect(self.edit_tool)
        button_layout.addWidget(self.edit_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def delete_tool(self):
        dialog = DeleteDialog("tool", self.tool_data['name'], self)
        try:
            if dialog.exec_() == QDialog.Accepted:
                delete_tool_from_db(self.tool_data['name'])
                self.setParent(None)
                self.deleteLater()
        except ValueError as e:
            QMessageBox.warning(self,"Tool",str(e))

    def edit_tool(self):
        # Tools are more complex to edit due to code, so we'll just open the tool tab
        dialog = NewIntegrationDialog(self)
        dialog.tabs.setCurrentIndex(0)  # Switch to Tool tab
        dialog.exec_()
        if self.parent() and hasattr(self.parent(), 'refresh'):
            self.parent().refresh()


class LLMItem(QWidget):
    def __init__(self, llm_data, parent=None):
        super().__init__(parent)
        self.llm_data = llm_data
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        # Main info
        info_layout = QVBoxLayout()
        model_label = QLabel(self.llm_data['model'])
        model_label.setFont(QFont("Arial", 12, QFont.Bold))
        url_label = QLabel(self.llm_data['base_url'])
        info_layout.addWidget(model_label)
        info_layout.addWidget(url_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            "background-color: #ff4444; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.delete_button.clicked.connect(self.delete_llm)
        button_layout.addWidget(self.delete_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 5px;"
        )
        self.edit_button.clicked.connect(self.edit_llm)
        button_layout.addWidget(self.edit_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def delete_llm(self):
        dialog = DeleteDialog("LLM", self.llm_data['model'], self)
        try:
            if dialog.exec_() == QDialog.Accepted:
                delete_llm_from_db(self.llm_data['model'])
                self.setParent(None)
                self.deleteLater()
        except ValueError as e:
            QMessageBox.warning(self,"LLM",str(e))

    def edit_llm(self):
        dialog = NewIntegrationDialog(self)
        dialog.tabs.setCurrentIndex(3)  # Switch to LLM tab

        # Pre-fill the form
        dialog.llm_model.setText(self.llm_data['model'])
        dialog.llm_api_key.setText(self.llm_data['api_key'])
        dialog.llm_base_url.setText(self.llm_data['base_url'])

        if dialog.exec_():
            if self.parent() and hasattr(self.parent(), 'refresh'):
                self.parent().refresh()

class IntegrationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CrewAI Manager")
        self.setFixedSize(1200, 900)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)  # Set layout directly on the dialog

        # Header
        header = QLabel("CrewAI Manager")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(header)

        # Controls
        controls_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        controls_layout.addWidget(self.refresh_button)

        self.add_button = QPushButton("Add New Integration")
        self.add_button.clicked.connect(self.show_new_integration_dialog)
        controls_layout.addWidget(self.add_button)

        layout.addLayout(controls_layout)

        # Main tabs
        self.main_tabs = QTabWidget()

        # Crews tab
        self.init_crews_tab()
        # Agents tab
        self.init_agents_tab()
        # Tasks tab
        self.init_tasks_tab()
        # Tools tab
        self.init_tools_tab()
        # LLMs tab
        self.init_llms_tab()

        layout.addWidget(self.main_tabs)
        self.setLayout(layout)  # Set the main layout on the dialog

    def init_crews_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.crews_scroll = QScrollArea()
        self.crews_scroll.setWidgetResizable(True)
        self.crews_widget = QWidget()
        self.crews_layout = QVBoxLayout(self.crews_widget)
        self.crews_scroll.setWidget(self.crews_widget)

        self.load_crews()

        layout.addWidget(self.crews_scroll)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Crews")

    def init_agents_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.agents_scroll = QScrollArea()
        self.agents_scroll.setWidgetResizable(True)
        self.agents_widget = QWidget()
        self.agents_layout = QVBoxLayout(self.agents_widget)
        self.agents_scroll.setWidget(self.agents_widget)

        self.load_agents()

        layout.addWidget(self.agents_scroll)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Agents")

    def init_tasks_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_widget = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_widget)
        self.tasks_scroll.setWidget(self.tasks_widget)

        self.load_tasks()

        layout.addWidget(self.tasks_scroll)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Tasks")

    def init_tools_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.tools_scroll = QScrollArea()
        self.tools_scroll.setWidgetResizable(True)
        self.tools_widget = QWidget()
        self.tools_layout = QVBoxLayout(self.tools_widget)
        self.tools_scroll.setWidget(self.tools_widget)

        self.load_tools()

        layout.addWidget(self.tools_scroll)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "Tools")

    def init_llms_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.llms_scroll = QScrollArea()
        self.llms_scroll.setWidgetResizable(True)
        self.llms_widget = QWidget()
        self.llms_layout = QVBoxLayout(self.llms_widget)
        self.llms_scroll.setWidget(self.llms_widget)

        self.load_llms()

        layout.addWidget(self.llms_scroll)
        tab.setLayout(layout)
        self.main_tabs.addTab(tab, "LLMs")

    def show_new_integration_dialog(self):
        dialog = NewIntegrationDialog(self)
        dialog.exec_()
        self.refresh()

    def load_crews(self):
        self.clear_layout(self.crews_layout)
        crews = get_crews_with_details()
        for crew in crews:
            item = CrewItem(crew['name'], self)
            self.crews_layout.addWidget(item)
        self.crews_layout.addStretch()

    def load_agents(self):
        self.clear_layout(self.agents_layout)
        agents = get_agents_with_details()
        for agent in agents:
            item = AgentItem(agent, self)
            self.agents_layout.addWidget(item)
        self.agents_layout.addStretch()

    def load_tasks(self):
        self.clear_layout(self.tasks_layout)
        tasks = get_tasks_with_details()
        for task in tasks:
            item = TaskItem(task, self)
            self.tasks_layout.addWidget(item)
        self.tasks_layout.addStretch()

    def load_tools(self):
        self.clear_layout(self.tools_layout)
        tools = get_tools_with_details()
        for tool in tools:
            item = ToolItem(tool, self)
            self.tools_layout.addWidget(item)
        self.tools_layout.addStretch()

    def load_llms(self):
        self.clear_layout(self.llms_layout)
        llms = get_llms_with_details()
        for llm in llms:
            item = LLMItem(llm, self)
            self.llms_layout.addWidget(item)
        self.llms_layout.addStretch()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh(self):
        current_tab = self.main_tabs.currentIndex()
        if current_tab == 0:
            self.load_crews()
        elif current_tab == 1:
            self.load_agents()
        elif current_tab == 2:
            self.load_tasks()
        elif current_tab == 3:
            self.load_tools()
        elif current_tab == 4:
            self.load_llms()


def execute_crew(crew_name: str, user_input: str) -> str:
    """
    Execute a crew with the given name using the provided user input.

    Args:
        crew_name (str): Name of the crew to execute
        user_input (str): Input to pass to the crew

    Returns:
        str: Response from the crew execution

    Raises:
        ValueError: If crew, agent, task, or LLM configuration is not found
    """
    try:
        # Get crew details from database
        cursor.execute("SELECT agents, tasks FROM crews WHERE name = ?", (crew_name,))
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"Crew '{crew_name}' not found in database")

        agents_json, tasks_json = result
        agents = json.loads(agents_json)
        tasks = json.loads(tasks_json)

        # Create Agent objects
        crew_agents = []
        agent_roles = {}  # Store agent roles for task assignment

        for agent_name in agents:
            # Get agent details from database
            cursor.execute(
                "SELECT id, role, goal, backstory, llm_id, tools FROM agents WHERE name = ?",
                (agent_name,)
            )
            agent_data = cursor.fetchone()

            if not agent_data:
                raise ValueError(f"Agent '{agent_name}' not found in database")

            agent_id, role, goal, backstory, llm_id, tools_str = agent_data

            # Store role for task assignment
            agent_roles[agent_name] = role

            # Get LLM details
            cursor.execute("SELECT model, api_key, base_url FROM llms WHERE id = ?", (llm_id,))
            llm_data = cursor.fetchone()

            if not llm_data:
                raise ValueError(f"LLM with ID {llm_id} not found in database")

            model, api_key, base_url = llm_data

            # Create LLM configuration
            llm_config = {
                "model": f"openai/{model}",
                "api_key": api_key,
                "base_url": base_url
            }
            print(llm_config)
            from crewai import LLM
            llm=LLM(
                model=f"openai/{model}",
                api_key=api_key,
                base_url=base_url
            )
            # Get tools
            agent_tools = []
            if tools_str and tools_str.strip():
                for tool_name in tools_str.split(","):
                    tool = load_tool_from_db(tool_name.strip())
                    if tool:
                        agent_tools.append(tool)

            # Create Agent
            agent = Agent(
                role=role,
                goal=goal,
                backstory=backstory,
                llm=llm,
                tools=agent_tools,
                verbose=True
            )
            crew_agents.append((agent_name, agent))  # Store agent with its name

        # Create Task objects
        crew_tasks = []
        for task_desc in tasks:
            # Get task details from database
            cursor.execute(
                "SELECT id, agent_id, expected_output FROM tasks WHERE description = ?",
                (task_desc,)
            )
            task_data = cursor.fetchone()

            if not task_data:
                raise ValueError(f"Task '{task_desc}' not found in database")

            task_id, agent_id, expected_output = task_data

            # Get agent name
            cursor.execute("SELECT name FROM agents WHERE id = ?", (agent_id,))
            agent_result = cursor.fetchone()

            if not agent_result:
                raise ValueError(f"Agent with ID {agent_id} for task not found")

            agent_name = agent_result[0]

            # Find the agent object by matching the stored name
            task_agent = next((agent for (name, agent) in crew_agents if name == agent_name), None)
            if not task_agent:
                raise ValueError(f"Agent '{agent_name}' for task not found in crew")

            # Create Task
            task = Task(
                description=task_desc,
                expected_output=expected_output,
                agent=task_agent
            )
            crew_tasks.append(task)

        # Extract just the agent objects for the crew
        agent_objects = [agent for (name, agent) in crew_agents]

        # Create and execute Crew
        crew = Crew(
            agents=agent_objects,
            tasks=crew_tasks,
            verbose=True
        )

        # Process the input and get the result
        result = crew.kickoff(inputs={"input": user_input})
        return str(result)

    except sqlite3.Error as e:
        return f"Database error: {str(e)}"
    except json.JSONDecodeError as e:
        return f"Invalid JSON data in crew configuration: {str(e)}"
    except Exception as e:
        return f"Error executing crew: {str(e)}"


if __name__ == "__main__":
    app = QApplication([])
    dialog = IntegrationsDialog()
    dialog.show()
    app.exec_()
