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
import time
from colorama import Fore, Style, init
from interpreter import interpreter
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.live import Live
import re
import json
import warnings
from config import  JARVIS_DIR
import threading

init(autoreset=True)
save_set = False
warnings.filterwarnings("ignore",category=SyntaxWarning)
# Define custom theme
custom_theme = Theme({
    "todo": "bold yellow",
    "error": "bold red",
    "note": "italic cyan",
    "code": "bold green",
    "default": "white",
    "prefix": "bold magenta"
})

console = Console(theme=custom_theme)


def typewriter_rich(
    content: str,
    is_code: bool = False,
    language: str = "python",
    delay: float = 0.015,
    show_panel: bool = True,
):
    def is_probable_code(text: str) -> bool:
        return bool(re.search(r"[\{\};]|def |class |import |=", text)) and len(text.split()) > 2

    def highlight_words(text: str) -> Text:
        rich_text = Text()
        for word in text.split():
            word_lower = word.lower()
            if "todo" in word_lower:
                style = "todo"
            elif "error" in word_lower or "fail" in word_lower:
                style = "error"
            elif "note" in word_lower or "hint" in word_lower:
                style = "note"
            else:
                style = "default"
            rich_text.append(word + " ", style=style)
        return rich_text


    # Code output
    if is_code or is_probable_code(content):
        syntax = Syntax(content, language, theme="monokai", line_numbers=False)
        if show_panel:
            console.print(Panel(syntax, title="📦 Code", border_style="code"))
        else:
            console.print(syntax)

    # Markdown output
    elif content.strip().startswith("#") or "**" in content or "\n" in content:
        console.print(Markdown(content, hyperlinks=True))

    # Simulated real-time text output
    else:
        styled_text = highlight_words(content)
        with Live("", refresh_per_second=30, console=console) as live:
            display_text = Text()
            for char in styled_text.plain:
                display_text.append(char, style=styled_text.get_style_at_offset(styled_text.plain.index(char)))
                live.update(display_text)
                time.sleep(delay)
            live.update(display_text)
        console.print()

def print_banner(message: str):
    width = 60
    top = "╔" + "═" * width + "╗"
    mid = f"║ {message.center(width - 2)} ║"
    bottom = "╚" + "═" * width + "╝"
    print(Fore.CYAN + Style.BRIGHT + top)
    print(Fore.CYAN + Style.BRIGHT + mid)
    print(Fore.CYAN + Style.BRIGHT + bottom)


def configure_interpreter():
    endpoint = os.getenv("ENDPOINT", "").lower()
    config_map = {
        "openai": {
            "model": os.getenv("OPENAI_API_MODEL", "gpt-4"),
            "base": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "key": os.getenv("OPENAI_API_KEY", ""),
        },
        "azure": {
            "model": os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4"),
            "base": os.getenv("AZURE_ENDPOINT", ""),
            "key": os.getenv("AZURE_API_KEY", ""),
            "version": os.getenv("AZURE_API_VERSION", "2023-12-01"),
            "type": "azure"
        },
        "groq": {
            "model": os.getenv("GROQ_API_MODEL"),
            "base": "https://api.groq.com/openai/v1",
            "key": os.getenv("GROQ_API_KEY")
        },
        "anthropic": {
            "model": os.getenv("ANTHROPIC_MODEL"),
            "base": "https://api.anthropic.com",
            "key": os.getenv("ANTHROPIC_API_KEY"),
            "type": "anthropic"
        },
        "ollama": {
            "model": os.getenv("OLLAMA_MODEL"),
            "base": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "key": "ollama"
        }
    }

    if endpoint not in config_map:
        console.print(f"[red]❌ Unknown or unsupported ENDPOINT: '{endpoint}'[/red]")
        return False

    cfg = config_map[endpoint]
    interpreter.llm.model = cfg["model"]
    interpreter.llm.api_key = cfg["key"]
    interpreter.llm.api_base = cfg.get("base")
    interpreter.llm.api_version = cfg.get("version", None)
    interpreter.llm.api_type = cfg.get("type", None)
    return True


def inter():
    global save_set
    print_banner("Welcome to J.A.R.V.I.S CLI Interface")

    if not configure_interpreter():
        return

    console.print(Panel("[bold green]Type your prompt below or type 'exit' to quit to save the conversation type '\\s'  and to delete the conversation type '\\d' [/bold green]"))
    session_path=os.path.join(JARVIS_DIR,"data","interpreter.json")
    if os.path.exists(session_path):
        with open(session_path,"r") as f:
            session_history = json.load(f)
    else:
        session_history = []

    while True:
        try:
            user_input = input(Fore.CYAN + Style.BRIGHT + "\n🧠 Ask J.A.R.V.I.S → ")
            print(save_set)
            if user_input.strip().lower() in ("exit", "quit", "q"):
                console.print(Panel("[bold green]👋 Exiting J.A.R.V.I.S. CLI! See you soon.[/bold green]"))
                break
            if user_input.strip().lower() in ('\\s'):
                with open(session_path,"w") as f:
                    json.dump(interpreter.messages,f)
                    save_set=True
                    continue
            if user_input.strip().lower() in ('\\d'):
                os.remove(session_path)
                interpreter.messages = []
                continue
            if not user_input.strip():
                continue

            interpreter.messages = session_history
            interpreter.llm.context_window=8000
            interpreter.llm.max_tokens=900
            interpreter.chat(user_input, display=False)
            response_chunks = interpreter.messages[interpreter.last_messages_count:]
            for chunk in response_chunks:
                if chunk.get('role') == 'assistant':
                    is_code = chunk.get("type") == "code"
                    lang = chunk.get("format")
                    typewriter_rich(chunk.get("content"), is_code=is_code, language=lang)
            if save_set:
                with open(session_path,"w") as f:
                    json.dump(interpreter.messages,f)
        except KeyboardInterrupt:
            print(Fore.RED + "\n[Interrupted]")
            break
        except Exception as e:
            console.print(f"[red]⚠️ Error: {str(e)}[/red]")


if __name__ == "__main__":
    inter()