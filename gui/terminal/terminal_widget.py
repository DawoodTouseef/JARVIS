from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCharFormat, QSyntaxHighlighter, QColor
from .terminal_manager import TerminalManager
from config import SessionManager
from typing import Dict,List
import re
from datetime import datetime

class TerminalHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the terminal widget."""
    def __init__(self, parent=None, theme: str = "default"):
        """Initialize the syntax highlighter with a theme.

        Args:
            parent: Parent QTextDocument.
            theme: Name of the theme to apply (e.g., 'default', 'dark', 'light').
        """
        super().__init__(parent)
        self.session_manager = SessionManager()
        self.session_manager.load_session()
        self.commands = ['clear', 'help', 'env', 'export', 'dir', 'ls', 'll', 'cd', 'pwd', 'mkdir', 'rm', 'touch', 'cat', 'gpt', 'history', 'write', 'undo', 'redo', 'stat']
        self.commands.append('suggest')
        self.theme = self.load_theme(theme)

        # Define formats
        self.command_format = QTextCharFormat()
        self.command_format.setForeground(QColor(self.theme["command"]))
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor(self.theme["error"]))
        self.path_format = QTextCharFormat()
        self.path_format.setForeground(QColor(self.theme["path"]))
        self.output_format = QTextCharFormat()
        self.output_format.setForeground(QColor(self.theme["output"]))
        self.prompt_format = QTextCharFormat()
        self.prompt_format.setForeground(QColor(self.theme["prompt"]))
        self.preview_format = QTextCharFormat()
        self.preview_format.setForeground(QColor(self.theme["preview"]))

    def load_theme(self, theme_name: str) -> Dict[str, str]:
        """Load a color theme for syntax highlighting.

        Args:
            theme_name: Name of the theme.

        Returns:
            Dict[str, str]: Dictionary of color codes for different elements.
        """
        themes = {
            "default": {
                "command": "cyan",
                "error": "red",
                "path": "yellow",
                "output": "white",
                "prompt": "green",
                "preview": "lightGray",
                "background": "black",
                "text": "white"
            },
            "dark": {
                "command": "#00FFFF",
                "error": "#FF5555",
                "path": "#FFFF55",
                "output": "#BBBBBB",
                "prompt": "#55FF55",
                "preview": "#888888",
                "background": "#1E1E1E",
                "text": "#DDDDDD"
            },
            "light": {
                "command": "#0088CC",
                "error": "#CC0000",
                "path": "#886600",
                "output": "#000000",
                "prompt": "#006600",
                "preview": "#666666",
                "background": "#F5F5F5",
                "text": "#000000"
            }
        }
        return themes.get(theme_name, themes["default"])

    def highlightBlock(self, text: str) -> None:
        """Highlight a block of text based on its content.

        Args:
            text: The text to highlight.
        """
        if text.startswith("VA:"):
            parts = text.split("$", 1)
            if len(parts) > 1:
                # Highlight prompt
                self.setFormat(0, len(parts[0]) + 1, self.prompt_format)
                command_line = parts[1].strip()
                if command_line:
                    command = command_line.split()[0]
                    if command in self.commands:
                        self.setFormat(len(parts[0]) + 1, len(text), self.command_format)
                    elif "command not found" in text:
                        self.setFormat(len(parts[0]) + 1, len(text), self.error_format)
                    # Highlight paths in commands like cd, cat, rm
                    if command in ['cd', 'cat', 'rm', 'write', 'stat']:
                        match = re.search(r'\s+([^\s]+)', command_line)
                        if match:
                            start = len(parts[0]) + 1 + match.start(1)
                            self.setFormat(start, len(match.group(1)), self.path_format)
        elif text.startswith("\t") or text.strip().startswith("Name:") or text.strip().startswith("dir") or text.strip().startswith("file"):
            # Highlight output (e.g., ls, cat, stat)
            self.setFormat(0, len(text), self.output_format)

class TerminalWidget(QTextEdit):
    def __init__(self, parent=None,theme: str = "default"):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10))
        self.setAcceptRichText(False)
        self.manager = TerminalManager.get_instance()
        self.current_input: str = ""
        self.prompt: str = ""
        self.theme: Dict[str, str] = TerminalHighlighter(theme=theme).theme
        self.setStyleSheet(f"background-color: {self.theme['background']}; color: {self.theme['text']};")
        self.highlighter = TerminalHighlighter(self.document(), theme=theme)
        self.input_start_pos: int = 0
        self.is_multiline: bool = False
        self.multiline_input: List[str] = []
        self.append(f"Virtual Assistant Terminal v1.0\nType 'help' for commands\n")
        self.show_prompt()

    def show_prompt(self) -> None:
        """Show the command prompt with current directory and optional user info."""
        username = self.manager.session.get_email().split('@')[0]
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.prompt = f"VA:{username}:{self.manager.get_current_dir()}$ "
        self.append(self.prompt)
        self.input_start_pos = self.textCursor().position()
        self.scrollToBottom()
        self.current_input = ""
        self.is_multiline = False
        self.multiline_input = []

    def update_input(self):
        """Update the current prompt line with input"""
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(self.prompt + self.current_input)
        self.setTextCursor(cursor)
        self.scrollToBottom()

    def scrollToBottom(self):
        """Move cursor and scrollbar to the bottom"""
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def keyPressEvent(self, event):
        """Handle key events, updating current line until Enter is pressed"""
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)

        if event.key() == Qt.Key_Return:
            self.manager.process_command(self.current_input, self)
            self.current_input = ""
            self.show_prompt()
        elif event.key() == Qt.Key_Backspace:
            if self.current_input:
                self.current_input = self.current_input[:-1]
                self.update_input()
        elif event.key() == Qt.Key_Up:
            command = self.manager.navigate_history(-1)
            if command is not None:
                self.current_input = command
                self.update_input()
        elif event.key() == Qt.Key_Down:
            command = self.manager.navigate_history(1)
            if command is not None:
                self.current_input = command
                self.update_input()
        elif event.key() == Qt.Key_Tab:
            self.manager.handle_tab_completion(self)
            self.update_input()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            self.append("^C")
            self.current_input = ""
            self.show_prompt()
        elif event.text():
            self.current_input += event.text()
            self.update_input()

    def close(self):
        """Clean up manager on close"""
        self.manager.release()