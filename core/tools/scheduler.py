from schedule import run_pending
import schedule
from datetime import datetime, timedelta
import threading
import time
from config import loggers

log=loggers["AGENTS"]

class ScheduleManager:
    def __init__(self):
        self.tasks = []
        self.running = False
        self.thread = None

    def start_scheduler(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()

    def _run_scheduler(self):
        while self.running:
            run_pending()
            time.sleep(1)

    def stop_scheduler(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def add_event(self, description: str, time_str: str, recurring: str = None) -> str:
        try:
            event_time = datetime.strptime(time_str, "%I:%M %p").time()
            if recurring:
                if recurring.lower() == "daily":
                    schedule.every().day.at(event_time.strftime("%H:%M")).do(
                        lambda: log.info(f"Reminder: {description}")
                    )
                elif recurring.lower() == "weekly":
                    schedule.every().week.at(event_time.strftime("%H:%M")).do(
                        lambda: log.info(f"Reminder: {description}")
                    )
                else:
                    return "Invalid recurring option, sir/madam. Use 'daily' or 'weekly'."
                return f"Recurring event '{description}' scheduled {recurring} at {time_str}, sir/madam."
            else:
                now = datetime.now()
                event_datetime = datetime.combine(now.date(), event_time)
                if event_datetime < now:
                    event_datetime += timedelta(days=1)
                schedule.every().day.at(event_time.strftime("%H:%M")).do(
                    lambda: log.info(f"Reminder: {description}")
                ).tag("one-time")
                return f"One-time event '{description}' scheduled for {time_str}, sir/madam."
        except ValueError:
            return "Invalid time format, sir/madam. Please use 'HH:MM AM/PM' (e.g., 3:00 PM)."

    def view_schedule(self) -> str:
        jobs = schedule.get_jobs()
        if not jobs:
            return "No events scheduled, sir/madam."
        return "\n".join([f"{job.next_run.strftime('%I:%M %p %b %d, %Y')}: {job.job_func.__closure__[0].cell_contents}" for job in jobs])

    def clear_schedule(self) -> str:
        schedule.clear()
        return "All scheduled events cleared, sir/madam."

    def add_task(self, task: str) -> str:
        self.tasks.append(task)
        return f"Task '{task}' added to your list, sir/madam."

    def view_tasks(self) -> str:
        if not self.tasks:
            return "No tasks in your list, sir/madam."
        return "\n".join([f"- {task}" for task in self.tasks])

schedule_manager = ScheduleManager()
schedule_manager.start_scheduler()

def create_schedule_tools():
    from langchain.tools import Tool
    return [
        Tool(
            name="schedule_event",
            func=lambda x: schedule_manager.add_event(x["description"], x["time"], x.get("recurring")),
            description="Schedule an event with description, time, and optional recurring (e.g., {'description': 'Meeting', 'time': '3:00 PM', 'recurring': 'daily'})"
        ),
        Tool(
            name="view_schedule",
            func=lambda _: schedule_manager.view_schedule(),
            description="View all scheduled events"
        ),
        Tool(
            name="clear_schedule",
            func=lambda _: schedule_manager.clear_schedule(),
            description="Clear all scheduled events"
        ),
        Tool(
            name="add_task",
            func=lambda x: schedule_manager.add_task(x),
            description="Add a task to your to-do list"
        ),
        Tool(
            name="view_tasks",
            func=lambda _: schedule_manager.view_tasks(),
            description="View all tasks in your to-do list"
        )
    ]