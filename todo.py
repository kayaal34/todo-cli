"""A tiny command-line todo manager that stores tasks in a JSON file."""

import argparse
import json
from datetime import datetime
from pathlib import Path

DEFAULT_DB = Path.home() / ".todo.json"


def load_tasks(db_path):
    if not db_path.exists():
        return []
    with db_path.open(encoding="utf-8") as f:
        return json.load(f)


def save_tasks(db_path, tasks):
    with db_path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def add_task(tasks, title, priority="normal"):
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "priority": priority,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    return task


def find_task(tasks, task_id):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"No task with id {task_id}")


def complete_task(tasks, task_id):
    task = find_task(tasks, task_id)
    task["done"] = True
    return task


def remove_task(tasks, task_id):
    task = find_task(tasks, task_id)
    tasks.remove(task)
    return task


def rename_task(tasks, task_id, title):
    task = find_task(tasks, task_id)
    task["title"] = title
    return task


def clear_done(tasks):
    remaining = [t for t in tasks if not t["done"]]
    removed = len(tasks) - len(remaining)
    tasks[:] = remaining
    return removed


PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}


def sort_tasks(tasks):
    """Open tasks first, then by priority, then by id."""
    return sorted(
        tasks,
        key=lambda t: (t["done"], PRIORITY_ORDER[t.get("priority", "normal")], t["id"]),
    )


def format_task(task):
    mark = "x" if task["done"] else " "
    flag = {"high": "!", "low": "-"}.get(task.get("priority", "normal"), " ")
    return f"[{mark}] {task['id']:>3} {flag} {task['title']}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simple todo list")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="path to the JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new task")
    p_add.add_argument("title", nargs="+")
    p_add.add_argument("-p", "--priority", choices=PRIORITY_ORDER, default="normal")

    sub.add_parser("list", help="list all tasks")

    p_done = sub.add_parser("done", help="mark a task as done")
    p_done.add_argument("id", type=int)

    p_rm = sub.add_parser("rm", help="remove a task")
    p_rm.add_argument("id", type=int)

    p_edit = sub.add_parser("edit", help="change a task's title")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("title", nargs="+")

    sub.add_parser("clear", help="remove all completed tasks")

    args = parser.parse_args(argv)
    tasks = load_tasks(args.db)

    if args.command == "add":
        task = add_task(tasks, " ".join(args.title), args.priority)
        save_tasks(args.db, tasks)
        print(f"Added task {task['id']}: {task['title']}")
    elif args.command == "list":
        if not tasks:
            print("No tasks yet.")
        for task in sort_tasks(tasks):
            print(format_task(task))
    elif args.command == "done":
        task = complete_task(tasks, args.id)
        save_tasks(args.db, tasks)
        print(f"Completed: {task['title']}")
    elif args.command == "rm":
        task = remove_task(tasks, args.id)
        save_tasks(args.db, tasks)
        print(f"Removed: {task['title']}")
    elif args.command == "edit":
        task = rename_task(tasks, args.id, " ".join(args.title))
        save_tasks(args.db, tasks)
        print(f"Updated task {task['id']}: {task['title']}")
    elif args.command == "clear":
        removed = clear_done(tasks)
        save_tasks(args.db, tasks)
        print(f"Cleared {removed} completed task(s)")


if __name__ == "__main__":
    main()
