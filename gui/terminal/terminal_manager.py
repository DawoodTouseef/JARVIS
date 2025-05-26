import os
import json
import openai
from .db.env_database import EnvDatabase
from .virtual_filesystem import VirtualFileSystem
from config import JARVIS_DIR
from jarvis_integration.models.command_history import CommandHistory
from jarvis_integration.internals.db import get_db
from config import SessionManager,loggers
from jarvis_integration.models.users import Users
from typing import List,Dict
from jarvis_integration.models.alias import Alias

logger=loggers['DB']

class TerminalManager:
    _instance = None
    _ref_count = 0
    session=SessionManager()
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        cls._ref_count += 1
        return cls._instance

    @classmethod
    def release(cls):
        cls._ref_count -= 1
        if cls._ref_count == 0:
            cls._instance.close()
            cls._instance = None

    def __init__(self):
        self.vfs = VirtualFileSystem()
        self.db = EnvDatabase()
        self.history = []
        self.history_index = -1
        self.load_history()
        self.openai_client = None
        self.init_openai()
        self.session.load_session()
        self.user_id=Users.get_user_by_email(self.session.get_email()).id
        self.aliases = self.get_aliases()

    def init_openai(self):
        """Initialize OpenAI client"""
        env_vars = self.db.get_all_vars()
        api_key = env_vars.get("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)

    def load_history(self):
        """Load command history from .has file"""
        try:
            with open(os.path.join(JARVIS_DIR, "data", "assistant_history.has"), 'r') as f:
                self.history = json.load(f)
        except FileNotFoundError:
            self.history = []

    def save_history(self):
        """Save command history to .has file"""
        with open(os.path.join(JARVIS_DIR, "data", "assistant_history.has"), 'w') as f:
            json.dump(self.history, f)

    def navigate_history(self, direction):
        """Navigate command history"""
        new_index = self.history_index + direction
        if 0 <= new_index < len(self.history):
            self.history_index = new_index
            return self.history[self.history_index]
        elif new_index == len(self.history):
            self.history_index = new_index
            return ""
        return None

    def get_current_dir(self):
        """Get current virtual directory"""
        return self.vfs.get_current_dir()

    def handle_tab_completion(self, widget):
        """Handle tab completion for commands and paths"""
        if not widget.current_input:
            return
        parts = widget.current_input.split()
        if not parts:
            return
        last_part = parts[-1]
        if len(parts) == 1:
            matches = [cmd for cmd in self.commands if cmd.startswith(last_part.lower())]
            matches.extend(self.get_command_suggestions(last_part))  # Add DB suggestions
            matches = list(dict.fromkeys(matches))  # Remove duplicates
            if len(matches) == 1:
                widget.current_input = matches[0]
                widget.update_input()
            elif matches:
                widget.append("\n" + "\t".join(matches))
                widget.show_prompt()
                widget.current_input = last_part
                widget.update_input()
        else:
            # Path completion
            try:
                matches = self.vfs.complete_path(last_part)
                if len(matches) == 1:
                    widget.current_input = ' '.join(parts[:-1] + [matches[0]])
                    widget.update_input()
                elif matches:
                    widget.append("\n" + "\t".join(matches))
                    widget.show_prompt()
                    widget.current_input = ' '.join(parts)
                    widget.update_input()
            except Exception:
                pass

    def process_command(self, command, widget):
        """Process entered command"""
        command = command.strip()
        if not command:
            widget.show_prompt()
            return

        self.save_command_to_db(command)

        # Add to history
        if command not in self.history:
            self.history.append(command)
            self.save_history()
        self.history_index = len(self.history)

        # Process commands
        cmd_lower = command.lower()
        parts = command.split()
        cmd = parts[0].lower() if parts else ""

        resolved_command = self.aliases.get(cmd, command)
        resolved_parts = resolved_command.split()
        resolved_cmd = resolved_parts[0].lower() if resolved_parts else ""
        if resolved_cmd == 'alias':
            if len(resolved_parts) < 3:
                widget.append("Usage: alias <name> <command>")
            else:
                alias, alias_cmd = resolved_parts[1], ' '.join(resolved_parts[2:])
                self.add_alias(alias, alias_cmd)
                widget.append(f"Alias '{alias}' set to '{alias_cmd}'")
        else:
            # Re-process resolved command
            if resolved_command != command:
                self.process_command(resolved_command, widget)
                return

        if cmd == 'clear' or cmd == 'cls':
            widget.clear()
        elif cmd == 'help':
            widget.append("Available commands:\n"
                          "  clear - Clear the terminal\n"
                          "  export KEY=VALUE - Set environment variable\n"
                          "  env - Show all environment variables\n"
                          "  dir/ls/ll - List directory contents\n"
                          "  cd PATH - Change directory\n"
                          "  pwd - Print working directory\n"
                          "  mkdir DIR - Create directory\n"
                          "  rm PATH - Remove file or directory\n"
                          "  touch FILE - Create empty file\n"
                          "  cat FILE - View file contents\n"
                          "  gpt QUERY - Query ChatGPT\n"
                          "  history - Show command history\n")
        elif cmd == 'history':
            for i, cmd in enumerate(self.history, 1):
                widget.append(f"{i:4}  {cmd}")
        elif cmd == 'env':
            env_vars = self.db.get_all_vars()
            if env_vars:
                for key, value in env_vars.items():
                    widget.append(f"{key}={value}")
            else:
                widget.append("No environment variables set")
        elif cmd == 'export':
            try:
                var_part = command[7:].strip()
                key, value = var_part.split('=', 1)
                key = key.strip()
                value = value.strip()
                self.db.set_var(key, value)
                if key == "OPENAI_API_KEY":
                    self.init_openai()
                widget.append(f"Exported {key}={value}")
            except ValueError:
                widget.append("Invalid export format. Use: export KEY=VALUE")
        elif cmd in ['dir', 'ls', 'll']:
            try:
                files = self.vfs.list_dir()
                if cmd == 'll':
                    for name, is_dir in files:
                        prefix = "dir" if is_dir else "file"
                        widget.append(f"{prefix:4} {name}")
                else:
                    for name, _ in files:
                        widget.append(name)
            except Exception as e:
                widget.append(f"Error: {str(e)}")
        elif cmd == 'cd':
            path = command[3:].strip()
            try:
                self.vfs.change_dir(path)
            except Exception as e:
                widget.append(f"cd: {str(e)}")
        elif cmd == 'pwd':
            widget.append(self.vfs.get_current_dir())
        elif cmd == 'mkdir':
            dir_name = command[6:].strip()
            try:
                self.vfs.create_dir(dir_name)
                widget.append(f"Created directory: {dir_name}")
            except Exception as e:
                widget.append(f"Error: {str(e)}")
        elif cmd == 'rm':
            path = command[3:].strip()
            try:
                self.vfs.remove(path)
                widget.append(f"Removed: {path}")
            except Exception as e:
                widget.append(f"Error: {str(e)}")
        elif cmd == 'touch':
            file_name = command[6:].strip()
            try:
                self.vfs.create_file(file_name)
                widget.append(f"Created file: {file_name}")
            except Exception as e:
                widget.append(f"Error: {str(e)}")
        elif cmd == 'cat':
            file_name = command[4:].strip()
            try:
                content = self.vfs.read_file(file_name)
                widget.append(content)
            except Exception as e:
                widget.append(f"Error: {str(e)}")
        elif cmd == 'gpt':
            if not self.openai_client:
                widget.append("Error: OPENAI_API_KEY not set. Use: export OPENAI_API_KEY=your_key")
            else:
                query = command[4:].strip()
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": query}]
                    )
                    widget.append(response.choices[0].message.content)
                except Exception as e:
                    widget.append(f"GPT Error: {str(e)}")
        elif cmd == 'suggest':
            partial = command[7:].strip()
            suggestions = self.get_command_suggestions(partial)
            widget.append("\n".join(suggestions) or "No suggestions")
        else:
            widget.append(f"command not found: {command}")

        widget.show_prompt()

    def save_command_to_db(self, command: str):
        try:
            with get_db() as db:
                db.add(CommandHistory(user_id=self.user_id, command=command))
                db.commit()
        except Exception as e:
            logger.error(f"Error saving command for user {self.user_id}: {e}")

    def get_command_suggestions(self, partial: str) -> List[str]:
        try:
            with get_db() as db:
                commands = db.query(CommandHistory).filter(
                    CommandHistory.user_id == self.user_id,
                    CommandHistory.command.ilike(f"{partial}%")
                ).order_by(CommandHistory.executed_at.desc()).limit(5).all()
                return [c.command for c in commands]
        except Exception as e:
            logger.error(f"Error retrieving suggestions for user {self.user_id}: {e}")
            return []

    def get_aliases(self) -> Dict[str, str]:
        try:
            with get_db() as db:
                aliases = db.query(Alias).filter_by(user_id=self.user_id).all()
                return {a.alias: a.command for a in aliases}
        except Exception as e:
            logger.error(f"Error retrieving aliases for user {self.user_id}: {e}")
            return {}

    def add_alias(self, alias: str, command: str) -> bool:
        try:
            with get_db() as db:
                db.add(Alias(user_id=self.user_id, alias=alias, command=command))
                db.commit()
                self.aliases[alias] = command
                return True
        except Exception as e:
            logger.error(f"Error adding alias for user {self.user_id}: {e}")
            return False

    def close(self):
        """Clean up resources"""
        self.db.close()
        self.vfs.close()