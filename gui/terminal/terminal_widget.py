from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCharFormat, QSyntaxHighlighter, QColor
from .terminal_manager import TerminalManager
from config import SessionManager


class TerminalHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_manager=SessionManager()
        self.session_manager.load_session()
        self.commands = ['clear', 'help', 'env', 'export', 'dir', 'ls', 'll', 'cd', 'pwd', 'mkdir', 'rm', 'touch', 'cat', 'gpt', 'history']
        self.commands.append('suggest')
        self.command_format = QTextCharFormat()
        self.command_format.setForeground(QColor("cyan"))
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor("red"))

    def highlightBlock(self, text):
        if text.startswith("VA:"):
            parts = text.split("$", 1)
            if len(parts) > 1:
                command = parts[1].strip().split()[0] if parts[1].strip() else ""
                if command in self.commands:
                    self.setFormat(0, len(text), self.command_format)
                elif command and "command not found" in text:
                    self.setFormat(0, len(text), self.error_format)

class TerminalWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10))
        self.setAcceptRichText(False)

        # Initialize terminal manager
        self.manager = TerminalManager.get_instance()

        # Input state
        self.current_input = ""
        self.prompt = f"VA:{self.manager.get_current_dir()}$ "

        # Syntax highlighter
        self.highlighter = TerminalHighlighter(self.document())

        # Initial message
        self.append(f"Virtual Assistant Terminal v1.0\nType 'help' for commands\n")
        self.show_prompt()

    def show_prompt(self):
        """Show prompt with current directory"""
        self.prompt = f"VA:{self.manager.get_current_dir()}$ "
        self.append(self.prompt)
        self.scrollToBottom()
        self.current_input = ""

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