from colorama import Fore, init

# Initialize colorama for cross-platform support
init(autoreset=True)

class STTException(Exception):
    def __init__(self, messages: str = None, status_code: int = None):
        super().__init__(messages)  # Pass the message to the base class
        self.status_code = status_code  # Store the status code as an instance variable

    def __str__(self):
        return Fore.RED + (self.args[0] if self.args else "An STT error occurred") + Fore.RESET
