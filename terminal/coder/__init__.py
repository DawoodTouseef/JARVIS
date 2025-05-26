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
from InquirerPy import inquirer
from components.coder.cli.console_terminal import MAIN_COLOR, ConsoleTerminal
from components.coder.core.project import Project
from components.coder.core.steps.steps import StepType



def configure():
    while True:
        step = inquirer.select(
            message="Step to be performed:",
            choices=[{"name": name.replace("_", " ").title(), "value": value} for name, value in StepType.__members__.items()],
            default=StepType.DEFAULT,
        ).execute()

        project_name = inquirer.text(
            message="Enter project name (optional):",
            validate=lambda x: True if x or x == "" else "Must provide a valid project name",
        ).execute()

        japanese_mode = inquirer.confirm(
            message="Enable Japanese mode?",
            default=False
        ).execute()

        review_mode = inquirer.confirm(
            message="Enable Review mode?",
            default=False
        ).execute()

        debug_mode = inquirer.confirm(
            message="Enable Debug mode?",
            default=False
        ).execute()

        plan_and_solve = inquirer.confirm(
            message="Enable Plan-and-Solve Prompting?",
            default=False
        ).execute()

        # ✅ Show summary
        print("\n🧾 Summary of J.A.R.V.I.S. Coder:")
        print(f"Step            : {step}")
        print(f"Project Name    : {project_name}")
        print(f"Japanese Mode   : {japanese_mode}")
        print(f"Review Mode     : {review_mode}")
        print(f"Debug Mode      : {debug_mode}")
        print(f"Plan & Solve    : {plan_and_solve}")

        confirm = inquirer.confirm(
            message="Is this configuration correct?",
            default=True
        ).execute()

        if confirm:
            return {
                "step": step,
                "project_name": project_name,
                "japanese_mode": japanese_mode,
                "review_mode": review_mode,
                "debug_mode": debug_mode,
                "plan_and_solve": plan_and_solve
            }

def coder_():
    from colorama import Fore, Style
    COMMAND_NAME="GPT ALL STAR"
    print(Fore.CYAN + Style.BRIGHT + "╔" + "═" * 60 + "╗")
    print(
        Fore.CYAN + Style.BRIGHT + "║" + Fore.GREEN + Style.BRIGHT + " 🤖  Entering AI-powered Code Generation Environment".ljust(
            60) + Fore.CYAN + "║")
    print(Fore.CYAN + Style.BRIGHT + "╚" + "═" * 60 + "╝")
    config=configure()
    console = ConsoleTerminal()
    console.title(COMMAND_NAME)

    project = Project(
        config["step"], config["project_name"], config["japanese_mode"], config["review_mode"], config["debug_mode"], config["plan_and_solve"]
    )
    project.start()
    project.finish()

    console.print(
        f"Thank you for using {COMMAND_NAME}! See you next time! :bye:",
        style=f"{MAIN_COLOR} bold",
    )

