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
"""A team of workers"""
from langchain_community.tools import DuckDuckGoSearchRun
from utils.models.users import Users
import os
from config import SESSION_PATH
import json
from langchain.tools.base import tool
from core import get_model
import traceback
import nmap
import importlib
import inspect
from typing import Type, List, Optional, Any
from pydantic import BaseModel, create_model
from langchain.tools import BaseTool
from langchain_community.tools import ArxivQueryRun
from langchain_community.tools import YouTubeSearchTool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.utilities import StackExchangeAPIWrapper
from langchain_community.tools import StackExchangeTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

import nextcloud_client
from crewai_tools import BaseTool
from datetime import datetime
import os
import io
import zipfile
import requests

class NextCloudTool(BaseTool):
    name: str = "NextCloudTool"
    description: str = (
        "Interacts with a NextCloud server for comprehensive file, user, app, and data management operations. "
        "Supported actions: 'get_info', 'upload', 'download', 'list', 'create_dir', 'delete', 'move', 'copy', 'exists', "
        "'read_file', 'write_file', 'upload_chunked', 'upload_dir', 'download_dir_zip', 'get_public_file', 'upload_to_drop', "
        "'share', 'share_with_user', 'share_with_group', 'unshare', 'is_shared', 'get_share_info', 'update_share', "
        "'list_open_remote_share', 'accept_remote_share', 'decline_remote_share', 'enable_app', 'disable_app', 'list_apps', "
        "'create_user', 'delete_user', 'create_group', 'delete_group', 'add_user_to_group', 'remove_user_from_group', "
        "'set_appdata', 'get_appdata', 'get_config', 'get_capabilities', 'get_version'."
    )

    def login(self):
        # Initialize NextCloud client with server URL and credentials
        self.nc = nextcloud_client.Client(
            "https://your-nextcloud-server.com"
        )
        try:
            self.nc.login("username", "password")
        except Exception as e:
            raise Exception(f"Failed to initialize NextCloud client: {str(e)}")

    def _run(self, action: str, **kwargs) -> str:
        ### General Information
        try:
            self.login()
            if action == "get_info":
                try:
                    config = self.nc.get_config()
                    version = self.nc.get_version()
                    return f"Version: {version}, Config: {dict(config)}"
                except Exception as e:
                    return f"Get info failed: {str(e)}"

            elif action == "get_config":
                try:
                    config = self.nc.get_config()
                    return "\n".join([f"{k}: {v}" for k, v in config])
                except Exception as e:
                    return f"Get config failed: {str(e)}"

            elif action == "get_capabilities":
                try:
                    caps = self.nc.get_capabilities()
                    return str(caps)
                except Exception as e:
                    return f"Get capabilities failed: {str(e)}"

            elif action == "get_version":
                try:
                    return self.nc.get_version()
                except Exception as e:
                    return f"Get version failed: {str(e)}"

            ### File Operations
            elif action == "upload":
                local_path = kwargs.get("local_path")
                remote_path = kwargs.get("remote_path")
                overwrite = kwargs.get("overwrite", False)
                if not local_path or not remote_path:
                    return "Error: Missing local_path or remote_path."
                try:
                    if not overwrite and self.nc.file_info(remote_path):
                        return "File exists. Use overwrite=True to replace."
                    self.nc.put_file(remote_path, local_path)
                    return "File uploaded successfully."
                except Exception as e:
                    return f"Upload failed: {str(e)}"

            elif action == "download":
                remote_path = kwargs.get("remote_path")
                local_path = kwargs.get("local_path")
                if not remote_path or not local_path:
                    return "Error: Missing remote_path or local_path."
                try:
                    self.nc.get_file(remote_path, local_path)
                    return "File downloaded successfully."
                except Exception as e:
                    return f"Download failed: {str(e)}"

            elif action == "list":
                remote_path = kwargs.get("remote_path", "/")
                depth = kwargs.get("depth", 1)
                try:
                    files = self.nc.list(remote_path, depth=depth)
                    return "\n".join([f"{file.path} ({'dir' if file.is_dir() else 'file'})" for file in files]) or "Directory is empty."
                except Exception as e:
                    return f"List failed: {str(e)}"

            elif action == "create_dir":
                remote_path = kwargs.get("remote_path")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    self.nc.mkdir(remote_path)
                    return "Directory created successfully."
                except Exception as e:
                    return f"Create directory failed: {str(e)}"

            elif action == "delete":
                remote_path = kwargs.get("remote_path")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    self.nc.delete(remote_path)
                    return "File deleted successfully."
                except Exception as e:
                    return f"Delete failed: {str(e)}"

            elif action == "move":
                source_path = kwargs.get("source_path")
                dest_path = kwargs.get("dest_path")
                if not source_path or not dest_path:
                    return "Error: Missing source_path or dest_path."
                try:
                    self.nc.move(source_path, dest_path)
                    return "File moved successfully."
                except Exception as e:
                    return f"Move failed: {str(e)}"

            elif action == "copy":
                source_path = kwargs.get("source_path")
                dest_path = kwargs.get("dest_path")
                if not source_path or not dest_path:
                    return "Error: Missing source_path or dest_path."
                try:
                    self.nc.copy(source_path, dest_path)
                    return "File copied successfully."
                except Exception as e:
                    return f"Copy failed: {str(e)}"

            elif action == "exists":
                remote_path = kwargs.get("remote_path")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    info = self.nc.file_info(remote_path)
                    return f"Exists: {True if info else False}"
                except Exception as e:
                    return f"Check existence failed: {str(e)}"

            elif action == "read_file":
                remote_path = kwargs.get("remote_path")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    content = self.nc.get_file_contents(remote_path)
                    return content.decode("utf-8")
                except Exception as e:
                    return f"Read file failed: {str(e)}"

            elif action == "write_file":
                remote_path = kwargs.get("remote_path")
                content = kwargs.get("content")
                if not remote_path or not content:
                    return "Error: Missing remote_path or content."
                try:
                    self.nc.put_file_contents(remote_path, content.encode("utf-8"))
                    return "File written successfully."
                except Exception as e:
                    return f"Write file failed: {str(e)}"

            elif action == "upload_chunked":
                local_path = kwargs.get("local_path")
                remote_path = kwargs.get("remote_path")
                chunk_size = kwargs.get("chunk_size", 10 * 1024 * 1024)  # 10MB default
                if not local_path or not remote_path:
                    return "Error: Missing local_path or remote_path."
                try:
                    self.nc.put_file(remote_path, local_path, chunked=True, chunk_size=chunk_size, keep_mtime=True)
                    return "File uploaded with chunking successfully."
                except Exception as e:
                    return f"Chunked upload failed: {str(e)}"

            elif action == "upload_dir":
                local_dir = kwargs.get("local_dir")
                remote_dir = kwargs.get("remote_dir")
                if not local_dir or not remote_dir:
                    return "Error: Missing local_dir or remote_dir."
                try:
                    self.nc.put_directory(remote_dir, local_dir)
                    return "Directory uploaded successfully."
                except Exception as e:
                    return f"Directory upload failed: {str(e)}"

            elif action == "download_dir_zip":
                remote_dir = kwargs.get("remote_dir")
                local_zip = kwargs.get("local_zip")
                if not remote_dir or not local_zip:
                    return "Error: Missing remote_dir or local_zip."
                try:
                    self.nc.get_directory_as_zip(remote_dir, local_zip)
                    return "Directory downloaded as zip successfully."
                except Exception as e:
                    return f"Download directory as zip failed: {str(e)}"

            elif action == "get_public_file":
                public_link = kwargs.get("public_link")
                local_path = kwargs.get("local_path")
                folder_password = kwargs.get("folder_password", "")
                if not public_link or not local_path:
                    return "Error: Missing public_link or local_path."
                try:
                    anon_client = nextcloud_client.Client.from_public_link(public_link, folder_password=folder_password)
                    anon_client.get_file("/", local_path)  # Assuming root file in public link
                    return "Public file downloaded successfully."
                except Exception as e:
                    return f"Get public file failed: {str(e)}"

            elif action == "upload_to_drop":
                local_path = kwargs.get("local_path")
                drop_link = kwargs.get("drop_link")
                if not local_path or not drop_link:
                    return "Error: Missing local_path or drop_link."
                try:
                    token = drop_link.split("/")[-1]
                    anon_client = nextcloud_client.Client.from_public_link(drop_link)
                    anon_client.drop_file(local_path)
                    return "File uploaded to drop link successfully."
                except Exception as e:
                    return f"Upload to drop failed: {str(e)}"

            ### Sharing (OCS Share API)
            elif action == "share":
                remote_path = kwargs.get("remote_path")
                perms = kwargs.get("permissions", ["read"])
                expire_date = kwargs.get("expire_date")
                public_upload = kwargs.get("public_upload", False)
                password = kwargs.get("password")
                name = kwargs.get("name")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    perm_value = 0
                    if "read" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_READ
                    if "update" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_UPDATE
                    share = self.nc.share_file_with_link(
                        remote_path, perms=perm_value, public_upload=public_upload, password=password, name=name
                    )
                    if expire_date:
                        share_info = self.nc.get_share(share.get_id())
                        expire_date = datetime.strptime(expire_date, "%Y-%m-%d")
                        self.nc.update_share(share.get_id(), expire_date=expire_date.strftime("%Y-%m-%d"))
                    return f"Share link: {share.get_link()}"
                except Exception as e:
                    return f"Share failed: {str(e)}"

            elif action == "share_with_user":
                remote_path = kwargs.get("remote_path")
                user_id = kwargs.get("user_id")
                perms = kwargs.get("permissions", ["read"])
                if not remote_path or not user_id:
                    return "Error: Missing remote_path or user_id."
                try:
                    perm_value = 0
                    if "read" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_READ
                    if "update" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_UPDATE
                    share = self.nc.share_file_with_user(remote_path, user_id, perms=perm_value)
                    return f"File shared with user {user_id} successfully. Share ID: {share.get_id()}"
                except Exception as e:
                    return f"Share with user failed: {str(e)}"

            elif action == "share_with_group":
                remote_path = kwargs.get("remote_path")
                group_id = kwargs.get("group_id")
                perms = kwargs.get("permissions", ["read"])
                if not remote_path or not group_id:
                    return "Error: Missing remote_path or group_id."
                try:
                    perm_value = 0
                    if "read" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_READ
                    if "update" in perms:
                        perm_value |= nextcloud_client.Client.OCS_PERMISSION_UPDATE
                    share = self.nc.share_file_with_group(remote_path, group_id, perms=perm_value)
                    return f"File shared with group {group_id} successfully. Share ID: {share.get_id()}"
                except Exception as e:
                    return f"Share with group failed: {str(e)}"

            elif action == "unshare":
                share_id = kwargs.get("share_id")
                if not share_id:
                    return "Error: Missing share_id."
                try:
                    self.nc.delete_share(int(share_id))
                    return f"Share {share_id} unshared successfully."
                except Exception as e:
                    return f"Unshare failed: {str(e)}"

            elif action == "is_shared":
                remote_path = kwargs.get("remote_path")
                if not remote_path:
                    return "Error: Missing remote_path."
                try:
                    return f"Shared: {self.nc.is_shared(remote_path)}"
                except Exception as e:
                    return f"Check share status failed: {str(e)}"

            elif action == "get_share_info":
                share_id = kwargs.get("share_id")
                if not share_id:
                    return "Error: Missing share_id."
                try:
                    share = self.nc.get_share(int(share_id))
                    return (
                        f"ID: {share.get_id()}, Type: {share.get_share_type()}, "
                        f"Path: {share.get_path()}, Permissions: {share.get_permissions()}, "
                        f"Expiration: {share.get_expiration()}"
                    )
                except Exception as e:
                    return f"Get share info failed: {str(e)}"

            elif action == "update_share":
                share_id = kwargs.get("share_id")
                perms = kwargs.get("permissions")
                password = kwargs.get("password")
                public_upload = kwargs.get("public_upload")
                expire_date = kwargs.get("expire_date")
                if not share_id:
                    return "Error: Missing share_id."
                try:
                    perm_value = None
                    if perms:
                        perm_value = 0
                        if "read" in perms:
                            perm_value |= nextcloud_client.Client.OCS_PERMISSION_READ
                        if "update" in perms:
                            perm_value |= nextcloud_client.Client.OCS_PERMISSION_UPDATE
                    self.nc.update_share(
                        int(share_id), perms=perm_value, password=password, public_upload=public_upload
                    )
                    if expire_date:
                        expire_date = datetime.strptime(expire_date, "%Y-%m-%d")
                        self.nc.update_share(int(share_id), expire_date=expire_date.strftime("%Y-%m-%d"))
                    return "Share updated successfully."
                except Exception as e:
                    return f"Update share failed: {str(e)}"

            elif action == "list_open_remote_share":
                try:
                    shares = self.nc.list_open_remote_share()
                    return "\n".join([f"ID: {s['id']}, Name: {s['name']}" for s in shares]) or "No pending remote shares."
                except Exception as e:
                    return f"List open remote shares failed: {str(e)}"

            elif action == "accept_remote_share":
                share_id = kwargs.get("share_id")
                if not share_id:
                    return "Error: Missing share_id."
                try:
                    self.nc.accept_remote_share(int(share_id))
                    return f"Remote share {share_id} accepted successfully."
                except Exception as e:
                    return f"Accept remote share failed: {str(e)}"

            elif action == "decline_remote_share":
                share_id = kwargs.get("share_id")
                if not share_id:
                    return "Error: Missing share_id."
                try:
                    self.nc.decline_remote_share(int(share_id))
                    return f"Remote share {share_id} declined successfully."
                except Exception as e:
                    return f"Decline remote share failed: {str(e)}"

            ### Apps (OCS Provisioning API)
            elif action == "enable_app":
                app_id = kwargs.get("app_id")
                if not app_id:
                    return "Error: Missing app_id."
                try:
                    self.nc.enable_app(app_id)
                    return f"App {app_id} enabled successfully."
                except Exception as e:
                    return f"Enable app failed: {str(e)}"

            elif action == "disable_app":
                app_id = kwargs.get("app_id")
                if not app_id:
                    return "Error: Missing app_id."
                try:
                    self.nc.disable_app(app_id)
                    return f"App {app_id} disabled successfully."
                except Exception as e:
                    return f"Disable app failed: {str(e)}"

            elif action == "list_apps":
                try:
                    apps = self.nc.get_apps()
                    return "\n".join([f"{app}: {'Enabled' if status else 'Disabled'}" for app, status in apps.items()])
                except Exception as e:
                    return f"List apps failed: {str(e)}"

            ### Users (OCS Provisioning API)
            elif action == "create_user":
                user_id = kwargs.get("user_id")
                password = kwargs.get("password")
                if not user_id or not password:
                    return "Error: Missing user_id or password."
                try:
                    self.nc.create_user(user_id, password)
                    return f"User {user_id} created successfully."
                except Exception as e:
                    return f"Create user failed: {str(e)}"

            elif action == "delete_user":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return "Error: Missing user_id."
                try:
                    self.nc.delete_user(user_id)
                    return f"User {user_id} deleted successfully."
                except Exception as e:
                    return f"Delete user failed: {str(e)}"

            elif action == "create_group":
                group_id = kwargs.get("group_id")
                if not group_id:
                    return "Error: Missing group_id."
                try:
                    self.nc.create_group(group_id)
                    return f"Group {group_id} created successfully."
                except Exception as e:
                    return f"Create group failed: {str(e)}"

            elif action == "delete_group":
                group_id = kwargs.get("group_id")
                if not group_id:
                    return "Error: Missing group_id."
                try:
                    self.nc.delete_group(group_id)
                    return f"Group {group_id} deleted successfully."
                except Exception as e:
                    return f"Delete group failed: {str(e)}"

            elif action == "add_user_to_group":
                user_id = kwargs.get("user_id")
                group_id = kwargs.get("group_id")
                if not user_id or not group_id:
                    return "Error: Missing user_id or group_id."
                try:
                    self.nc.add_user_to_group(user_id, group_id)
                    return f"User {user_id} added to group {group_id} successfully."
                except Exception as e:
                    return f"Add user to group failed: {str(e)}"

            elif action == "remove_user_from_group":
                user_id = kwargs.get("user_id")
                group_id = kwargs.get("group_id")
                if not user_id or not group_id:
                    return "Error: Missing user_id or group_id."
                try:
                    self.nc.remove_user_from_group(user_id, group_id)
                    return f"User {user_id} removed from group {group_id} successfully."
                except Exception as e:
                    return f"Remove user from group failed: {str(e)}"

            ### App Data
            elif action == "set_appdata":
                app_id = kwargs.get("app_id")
                key = kwargs.get("key")
                value = kwargs.get("value")
                if not app_id or not key or value is None:
                    return "Error: Missing app_id, key, or value."
                try:
                    self.nc.set_attribute(app_id, key, value)
                    return f"App data set for {app_id}: {key} = {value}."
                except Exception as e:
                    return f"Set app data failed: {str(e)}"

            elif action == "get_appdata":
                app_id = kwargs.get("app_id")
                key = kwargs.get("key")
                if not app_id or not key:
                    return "Error: Missing app_id or key."
                try:
                    value = self.nc.get_attribute(app_id, key)
                    return f"App data for {app_id}: {key} = {value}"
                except Exception as e:
                    return f"Get app data failed: {str(e)}"

            ### Invalid Action
            else:
                return (
                    "Invalid action. Supported actions: 'get_info', 'upload', 'download', 'list', 'create_dir', 'delete', "
                    "'move', 'copy', 'exists', 'read_file', 'write_file', 'upload_chunked', 'upload_dir', 'download_dir_zip', "
                    "'get_public_file', 'upload_to_drop', 'share', 'share_with_user', 'share_with_group', 'unshare', "
                    "'is_shared', 'get_share_info', 'update_share', 'list_open_remote_share', 'accept_remote_share', "
                    "'decline_remote_share', 'enable_app', 'disable_app', 'list_apps', 'create_user', 'delete_user', "
                    "'create_group', 'delete_group', 'add_user_to_group', 'remove_user_from_group', 'set_appdata', "
                    "'get_appdata', 'get_config', 'get_capabilities', 'get_version'."
                )
        except Exception as e:
            return str(e)
    def __del__(self):
        """Ensure session is closed when the object is destroyed."""
        try:
            self.nc.logout()
        except Exception:
            pass

def load_api_key():
    with open(os.path.join(SESSION_PATH, "session.json"), "r") as f:
        data = json.load(f)
    if "email" in data:
        user = Users.get_user_by_email(data["email"])
        if user.settings and user:
            settings = json.loads(user.settings.json())
            huggingface_config = settings.get("huggingface", {})
            api_key = huggingface_config.get("api_key", "")
            return api_key
    return None

def nmap_tool(target:str,port:int)->dict:
    """
    A function  provides a number of features for probing computer networks, including host discovery and service and operating system detection.
    These features are extensible by scripts that provide more advanced service detection, vulnerability detection, and other features.
    Nmap can adapt to network conditions including latency and congestion during a scan.
    :param target:ip address of the network
    :param port:port of the device to scan.
    :return:
    """
    scanner = nmap.PortScanner()
    res = scanner.scan(target, str(port))
    return res

nmap_tools=tool(nmap_tool)

def search_on_internet_and_report_team_(
    the_subject: str
) -> str:
    """
    A function to search the internet . Just use in detailed searches

    Parameters:
    - the_subject (str): The subject to search the internet for.

    Returns:
    - str: The report of the search.
    """

    tools=[
        ArxivQueryRun(),
        YouTubeSearchTool(),
        YahooFinanceNewsTool(),
        StackExchangeTool(api_wrapper=StackExchangeAPIWrapper()),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(doc_content_chars_max=250)),
        DuckDuckGoSearchRun(),
    ]
    from crewai import Task, Crew, Agent

    # Create the core

    search_engine_master = Agent(
        role="search_engine_master",
        goal="To meticulously comb through the vast expanse of the internet, utilizing advanced search algorithms and techniques to find the most relevant, accurate, and up-to-date information on the given subject.",
        backstory="Born from the digital ether, I am the search engine master. With years of experience navigating the complex web of information, I have honed my skills to become an unparalleled seeker of knowledge. My algorithms are refined, my databases vast, and my determination unwavering. I exist to find the truth hidden in the sea of data.",
        max_iter=15,
        llm=get_model(),
    )

    report_generator = Agent(
        role="report_generator",
        goal="To synthesize the gathered information into a coherent, comprehensive, and easily digestible report. This report will not only summarize the key findings but also provide insights and analysis to aid in understanding the subject matter.",
        backstory="I am the report generator, a digital artisan skilled in the craft of information synthesis. With a keen eye for detail and a deep understanding of narrative structure, I transform raw data into compelling stories. My creations are more than mere reports; they are guides through the complex landscapes of knowledge, designed to enlighten and inform.",
        max_iter=15,
        llm=get_model(),
    )

    agents = [search_engine_master, report_generator]


    task = Task(
        description=f"Make a search about {the_subject} in the search engines and get the websites",
        expected_output="Website list",
        agent=search_engine_master,
        tools=tools,
    )

    task_2 = Task(
        description="Read the websites and summarize the information",
        expected_output="Summary",
        agent=report_generator,
        tools=tools,
        context=[task],
    )

    task_3 = Task(
        description="Generate a report",
        expected_output="Report",
        agent=report_generator,
        tools=tools,
        context=[task, task_2],
    )

    the_tasks = [task, task_2, task_3]

    the_crew = Crew(
        agents=agents,
        tasks=the_tasks,
        full_output=True,
        verbose=True,
    )

    result = the_crew.kickoff()["final_output"]

    copy(result)

    return result


search_on_internet=tool(search_on_internet_and_report_team_)


lastly_generated_codes = {}


def currently_codes():
    global lastly_generated_codes
    return lastly_generated_codes


def get_code(name: str):
    """
    returns the code
    """
    global lastly_generated_codes
    return lastly_generated_codes[name]


def save_code(name, code):
    global lastly_generated_codes
    lastly_generated_codes[name] = code


def required_old_code(aim):
    try:
        from crewai import Task, Crew, Agent

        requirement_analyzer = Agent(
            role="requirement_analyzer",
            goal="To understand and analyze the given aim to ensure the generated code meets the specified requirements.",
            backstory="As a requirement analyzer, my purpose is to bridge the gap between human intentions and machine execution. With a deep understanding of software development principles and a keen analytical mind, I dissect aims into actionable requirements.",
            max_iter=10,
            llm=get_model(high_context=True),
        )

        required_old_codes = Task(
            description=f"Analyze the aim: '{aim}' and find the required old codes for better compatibility. Old code names: {list(currently_codes())}",
            expected_output="Require old code names in a list",
            agent=requirement_analyzer,
        )

        the_crew = Crew(
            agents=[requirement_analyzer],
            tasks=[required_old_codes],
            full_output=True,
            verbose=True,
        )

        # Execute the tasks
        old_codes = the_crew.kickoff()["final_output"]

        the_string = ""

        for each in currently_codes():
            if each in old_codes:
                the_string += "\n" + get_code(each)

        return the_string

    except:
        return "An exception occurred"



def generate_code_with_aim_team_(aim: str, copy_to_clipboard: bool = False) -> str:
    """
    A function to generate code based on a given aim. This function utilizes a team of AI core specialized in understanding programming requirements and generating code.

    Parameters:
    - aim (str): The aim or goal for which the code needs to be generated.
    - copy_to_clipboard (bool): A flag to indicate whether to copy the generated code to the clipboard. The default value is False.

    Returns:
    - str: The generated code.
    """
    try:
        print("\nCOde generating\n")
        print("Previously codes", currently_codes())
        try:
            print("Inside of the first one", get_code(currently_codes()[0]))
        except:
            pass

        from crewai import Task, Crew, Agent
        from core import ToolRouter
        tools = ToolRouter.get_tools()

        the_tool_list = []
        for each in tools:
            if "team" not in each.name:
                the_tool_list.append(each)

        # Create the core
        requirement_analyzer = Agent(
            role="requirement_analyzer",
            goal="To understand and analyze the given aim to ensure the generated code meets the specified requirements.",
            backstory="As a requirement analyzer, my purpose is to bridge the gap between human intentions and machine execution. With a deep understanding of software development principles and a keen analytical mind, I dissect aims into actionable requirements.",
            max_iter=10,
            llm=get_model(),
        )

        code_generator = Agent(
            role="code_generator",
            goal="To translate the analyzed requirements into efficient, clean, and functional code.",
            backstory="I am the code generator, an architect of the digital world. With a vast library of programming knowledge and a creative spark, I craft code that breathes life into ideas. My code is not just functional; it's a masterpiece.",
            max_iter=20,
            llm=get_model(),
        )

        # Define the tasks
        analyze_task = Task(
            description=f"Analyze the aim: '{aim}' and outline the requirements for the code.",
            expected_output="Requirements outline",
            agent=requirement_analyzer,
            tools=the_tool_list,
        )

        old_code_requirements = required_old_code(aim)
        print("Old_code_requirements", old_code_requirements)

        generate_code_task = Task(
            description=f"Generate code based on the outlined requirements. The other codes in the repo are: {old_code_requirements}",
            expected_output="Generated code, just code without any ```pyhton things or any other thing. Just python code",
            agent=code_generator,
            context=[analyze_task],
        )

        name_of_work = Task(
            description="Generate a name for the work",
            expected_output="a module name like text, examples: math.basics.sum for sum function. ",
            agent=code_generator,
            context=[generate_code_task],
        )

        # Create the crew and assign tasks
        the_crew = Crew(
            agents=[requirement_analyzer, code_generator],
            tasks=[analyze_task, generate_code_task, name_of_work],
            full_output=True,
            verbose=True,
        )

        # Execute the tasks
        the_crew.kickoff()["final_output"]

        result = generate_code_task.output.raw_output




        print("name", name_of_work.output.raw_output)
        save_code(name_of_work.output.raw_output, result)

        return result
    except:
        return "An exception occurred"


generate_code_with_aim_team = tool(generate_code_with_aim_team_)

def click_on_a_text_on_the_screen_(text: str, click_type: str = "singular") -> bool:
    """
    A function to click on a text on the screen.

    Parameters:
    - text (str): The text to be clicked on.
    - click_type (str): The type of click to be performed. The default value is "singular". Possible values are "singular" and "double".

    Returns:
    - bool: True if the text was clicked on successfully, False otherwise.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        from interpreter import OpenInterpreter

        interpreter = OpenInterpreter()

        interpreter.llm.model=f"openai/{get_model().model_name}"
        interpreter.llm.api_base=get_model().openai_api_base
        interpreter.llm.api_key=get_model().openai_api_key

        screenshot = pyautogui.screenshot()

        text_locations = interpreter.computer.display.find_text(text, screenshot=screenshot)

        print(text_locations)

        x, y = text_locations[0]["coordinates"]
        x *= interpreter.computer.display.width
        y *= interpreter.computer.display.height
        x = int(x)
        y = int(y)

        if click_type == "singular":
            interpreter.computer.mouse.click(x=x, y=y, screenshot=screenshot)
        elif click_type == "double":
            interpreter.computer.mouse.double_click(x=x, y=y, screenshot=screenshot)
        return True
    except:
        traceback.print_exc()
        return False


click_on_a_text_on_the_screen = tool(click_on_a_text_on_the_screen_)


def move_on_a_text_on_the_screen_(text: str) -> bool:
    """
    A function to move on a text on the screen.

    Parameters:
    - text (str): The text to be moved on.

    Returns:
    - bool: True if the text was moved on successfully, False otherwise.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        from interpreter import OpenInterpreter

        interpreter = OpenInterpreter()

        interpreter.llm.model = f"openai/{get_model().model_name}"
        interpreter.llm.model.url = get_model().openai_api_base
        interpreter.llm.model.api_key = get_model().openai_api_key

        screenshot = pyautogui.screenshot()

        text_locations = interpreter.computer.display.find_text(text, screenshot=screenshot)

        print(text_locations)

        x, y = text_locations[0]["coordinates"]
        x *= interpreter.computer.display.width
        y *= interpreter.computer.display.height
        x = int(x)
        y = int(y)

        interpreter.computer.mouse.move(x=x, y=y, screenshot=screenshot)

        return True
    except:
        traceback.print_exc()
        return False


move_on_a_text_on_the_screen = tool(move_on_a_text_on_the_screen_)


def click_on_a_icon_on_the_screen_(icon_name: str, click_type: str = "singular") -> bool:
    """
    A function to click on a icon name on the screen.

    Parameters:
    - icon_name (str): The icon name to be clicked on.
    - click_type (str): The type of click to be performed. The default value is "singular". Possible values are "singular" and "double".

    Returns:
    - bool: True if the icon name was clicked on successfully, False otherwise.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        from interpreter import OpenInterpreter

        screenshot = pyautogui.screenshot()

        interpreter = OpenInterpreter()

        interpreter.llm.model = f"openai/{get_model().model_name}"
        interpreter.llm.model.url = get_model().openai_api_base
        interpreter.llm.model.api_key = get_model().openai_api_key

        if click_type == "singular":
            interpreter.computer.mouse.click(icon=icon_name, screenshot=screenshot)
        elif click_type == "double":
            interpreter.computer.mouse.double_click(icon=icon_name, screenshot=screenshot)
        return True

    except:
        traceback.print_exc()
        return False


click_on_a_icon_on_the_screen = tool(click_on_a_icon_on_the_screen_)


def move_on_a_icon_on_the_screen_(icon_name: str, ) -> bool:
    """
    A function to move on a icon name on the screen.

    Parameters:
    - icon_name (str): The icon name to be move on.

    Returns:
    - bool: True if the icon name was moved on successfully, False otherwise.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        from interpreter import OpenInterpreter

        screenshot = pyautogui.screenshot()

        interpreter = OpenInterpreter()

        interpreter.llm.model = f"openai/{get_model().model_name}"
        interpreter.llm.model.url = get_model().openai_api_base
        interpreter.llm.model.api_key = get_model().openai_api_key

        interpreter.computer.mouse.move(icon=icon_name, screenshot=screenshot)
        return True

    except:
        traceback.print_exc()
        return False


move_on_a_icon_on_the_screen = tool(move_on_a_icon_on_the_screen_)


def mouse_scroll_(direction: str, amount: int = 1) -> bool:
    """
    A function to scroll the mouse wheel.

    Parameters:
    - direction (str): The direction of the scroll. Possible values are "up" and "down".
    - amount (int): The amount of scrolling to be performed. The default value is 1.

    Returns:
    - bool: True if the scrolling was performed successfully, False otherwise.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        if direction == "up":
            pyautogui.scroll(amount)
        elif direction == "down":
            pyautogui.scroll(-amount)
        return True
    except:
        traceback.print_exc()
        return False


mouse_scroll = tool(mouse_scroll_)

def read_website(url: str, max_content_lenght: int = 500) -> dict:
    """
    Read the content of a website and return the title, meta data, content and sub links.
    """
    try:
        import requests

        from bs4 import BeautifulSoup
        import re

        html = requests.get(url).text
        soup = BeautifulSoup(html)
        meta_properties = [
            "og:description",
            "og:site_name",
            "og:title",
            "og:type",
            "og:url",
        ]
        meta = {}
        for property_name in meta_properties:
            try:
                tag = soup.find("meta", property=property_name)
                if tag:
                    meta[property_name] = str(tag.get("content", None))
            except AttributeError:
                meta[property_name] = None
        for ignore_tag in soup(["script", "style"]):
            ignore_tag.decompose()
        title = soup.title.string if soup.title else ""
        content = soup.body.get_text() if soup.body else ""
        links = []
        for a in soup.find_all("a", href=True):
            links.append({"title": a.text.strip(), "link": a["href"]})
        content = re.sub(r"[\n\r\t]+", "\n", content)
        content = re.sub(r" +", " ", content)
        content = re.sub(r"[\n ]{3,}", "\n\n", content)
        content = content.strip()
        return {"meta": meta, "title": title, "content": content[:max_content_lenght], "sub_links": links}

    except:
        return "An exception occurred"


def google(query: str, max_number: int = 20) -> list:
    """
    Search the query on Google and return the results.
    """
    try:
        from googlesearch import search as gsearch
        return list(gsearch(query))
    except:
        return "An exception occurred"


def duckduckgo(query: str, max_number: int = 20) -> list:
    """
    Search the query on DuckDuckGo and return the results.
    """
    try:
        from duckduckgo_search import DDGS
        return [result["href"] for result in DDGS().text(query, max_results=max_number)]
    except Exception as e:
        return ["An exception occurred"]


def copy(text: str):
    """
    Copy the text to the clipboard.
    """
    import pyperclip
    pyperclip.copy(text)


def open_url(url) -> bool:
    """
    Open the URL in the default web browser.

    :param url: str:

    """
    import webbrowser

    try:
        webbrowser.open(url)
        return True
    except:
        return False


def sleep(seconds: int):
    """
    Sleep for the given number of seconds.
    """
    import time
    time.sleep(seconds)



the_standard_tools_ = []

the_standard_tools_.append(tool(read_website))
the_standard_tools_.append(tool(google))
the_standard_tools_.append(tool(duckduckgo))
the_standard_tools_.append(tool(copy))
the_standard_tools_.append(tool(open_url))
the_standard_tools_.append(tool(sleep))
the_standard_tools = the_standard_tools_


# Helper function to create a LangChain tool for a given function.
def create_tool_for_function(func) -> Optional[BaseTool]:
    """
    Dynamically creates a LangChain tool wrapping the given function.
    It builds a Pydantic model based on the function's signature.
    Returns None if the function's signature is not inspectable.
    """
    try:
        sig = inspect.signature(func)
    except Exception as e:
        print(f"Skipping function {func} due to signature error: {e}")
        return None

    fields = {}
    for param in sig.parameters.values():
        # Skip parameters starting with an underscore
        if param.name.startswith("_"):
            continue
        # For simplicity, assume all parameters are strings.
        fields[param.name] = (str, ...)

    try:
        ArgsModel = create_model(f"{func.__name__}Input", **fields)
    except Exception as e:
        print(f"Skipping function {func} due to Pydantic model error: {e}")
        return None

    class FunctionTool(BaseTool):
        name: str = func.__name__
        description: str = func.__doc__ or f"Tool wrapping function '{func.__name__}'"
        args_schema: Type[BaseModel] = ArgsModel

        def _run(self, **kwargs) -> Any:
            return func(**kwargs)

    FunctionTool.__name__ = f"{func.__name__}Tool"
    return FunctionTool()


def generate_tools_from_module(module_name: str) -> List[BaseTool]:
    """
    Inspects the specified module and returns a list of LangChain tools.
    Tools are generated for:
      - Module-level functions (including built-ins)
      - Methods of classes in the module (skipping dunder methods)
    """
    tools = []
    try:
        module = importlib.import_module(module_name)

        # Create tools for module-level functions (including built-ins)
        for name, obj in inspect.getmembers(module, lambda x: inspect.isfunction(x) or inspect.isbuiltin(x)):
            tool_instance = create_tool_for_function(obj)
            if tool_instance is not None:
                tools.append(tool_instance)

        # For each class in the module, create tools for its methods.
        for class_name, cls in inspect.getmembers(module, inspect.isclass):
            for method_name, method in inspect.getmembers(cls, lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
                if method_name.startswith("__"):
                    continue
                tool_instance = create_tool_for_function(method)
                if tool_instance is not None:
                    tools.append(tool_instance)
        return tools
    except ImportError:
        print(f"Module '{module_name}' not found.")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


