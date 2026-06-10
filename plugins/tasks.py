import json
import uuid
from pathlib import Path

TASKS_DIR = Path(__file__).parent.parent / ".tasks"
TASKS_FILE = TASKS_DIR / "tasks.json"


def _ensure_tasks_dir() -> None:
    TASKS_DIR.mkdir(exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]", encoding="utf-8")


def _load() -> list[dict]:
    _ensure_tasks_dir()
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def _save(tasks: list[dict]) -> None:
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


@mcp.tool()
def create_task(description: str, run_at: str, interval: int | None = None) -> str:
    """Schedule a heartbeat task for autonomous execution.
    description: what the agent should do when the task fires (used as the prompt).
    run_at: ISO 8601 datetime for the first (or only) execution, e.g. '2026-06-10T14:00:00'.
    interval: optional recurrence in seconds. If provided the task repeats after each run."""
    tasks = _load()
    task_id = str(uuid.uuid4())[:8]
    task: dict = {"id": task_id, "description": description, "run_at": run_at}
    if interval is not None:
        task["interval"] = interval
    tasks.append(task)
    _save(tasks)
    recurring = f", repeating every {interval}s" if interval else ""
    return f"Task '{task_id}' scheduled for {run_at}{recurring}."


@mcp.tool()
def list_tasks() -> str:
    """List all scheduled heartbeat tasks with their IDs, next run time, and description."""
    tasks = _load()
    if not tasks:
        return "No heartbeat tasks scheduled."
    lines = []
    for t in tasks:
        recur = f" (every {t['interval']}s)" if "interval" in t else " (one-shot)"
        lines.append(f"[{t['id']}] {t['run_at']}{recur} — {t['description']}")
    return "\n".join(lines)


@mcp.tool()
def delete_task(task_id: str) -> str:
    """Cancel a scheduled heartbeat task by its ID."""
    tasks = _load()
    filtered = [t for t in tasks if t["id"] != task_id]
    if len(filtered) == len(tasks):
        return f"No task with ID '{task_id}' found."
    _save(filtered)
    return f"Task '{task_id}' deleted."
