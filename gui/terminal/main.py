import sys
from PyQt5.QtWidgets import QApplication, QAction, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon
from gui.terminal.terminal_dialog import TerminalDialog
from config import SessionManager

class TerminalApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.terminals = []

        # System tray icon
        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("terminal"))
        menu = QMenu()
        new_terminal = QAction("New Terminal", self)
        new_terminal.triggered.connect(self.open_terminal)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit)
        menu.addAction(new_terminal)
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

        # Open first terminal
        self.open_terminal()

    def open_terminal(self):
        terminal = TerminalDialog()
        self.terminals.append(terminal)
        terminal.show()


if __name__ == '__main__':
    ses=SessionManager()
    ses.create_session("tdawood140@gmail.com")
    app = TerminalApp(sys.argv)
    sys.exit(app.exec_())