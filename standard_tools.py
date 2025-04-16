
"""A team of workers"""
from utils.models.users import Users
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

import nextcloud_client
from crewai_tools import BaseTool
from datetime import datetime
import os

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


