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


def add_task(tasks, title):
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    return task


def format_task(task):
    mark = "x" if task["done"] else " "
    return f"[{mark}] {task['id']:>3}  {task['title']}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simple todo list")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="path to the JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new task")
    p_add.add_argument("title", nargs="+")

    sub.add_parser("list", help="list all tasks")

    args = parser.parse_args(argv)
    tasks = load_tasks(args.db)

    if args.command == "add":
        task = add_task(tasks, " ".join(args.title))
        save_tasks(args.db, tasks)
        print(f"Added task {task['id']}: {task['title']}")
    elif args.command == "list":
        if not tasks:
            print("No tasks yet.")
        for task in tasks:
            print(format_task(task))


if __name__ == "__main__":
    main()
