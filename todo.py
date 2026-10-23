"""A tiny command-line todo manager that stores tasks in a JSON file."""

import argparse
import csv
import io
import json
from datetime import date, datetime
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


def add_task(tasks, title, priority="normal", due=None):
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "priority": priority,
        "due": due.isoformat() if due else None,
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


def filter_tasks(tasks, search=None, only_open=False):
    result = tasks
    if search:
        needle = search.casefold()
        result = [t for t in result if needle in t["title"].casefold()]
    if only_open:
        result = [t for t in result if not t["done"]]
    return result


PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}


def sort_tasks(tasks):
    """Open tasks first, then by priority, then by id."""
    return sorted(
        tasks,
        key=lambda t: (t["done"], PRIORITY_ORDER[t.get("priority", "normal")], t["id"]),
    )


def is_overdue(task, today=None):
    due = task.get("due")
    return bool(due) and not task["done"] and date.fromisoformat(due) < (today or date.today())


def format_task(task, today=None):
    mark = "x" if task["done"] else " "
    flag = {"high": "!", "low": "-"}.get(task.get("priority", "normal"), " ")
    line = f"[{mark}] {task['id']:>3} {flag} {task['title']}"
    if task.get("due"):
        line += f"  (due {task['due']}{', OVERDUE' if is_overdue(task, today) else ''})"
    return line


def export_markdown(tasks):
    """Render tasks as a Markdown checklist, open tasks first."""
    lines = []
    for task in sort_tasks(tasks):
        mark = "x" if task["done"] else " "
        extras = []
        if task.get("priority", "normal") != "normal":
            extras.append(task["priority"])
        if task.get("due"):
            extras.append(f"due {task['due']}")
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"- [{mark}] {task['title']}{suffix}")
    return "\n".join(lines) + ("\n" if lines else "")


EXPORT_FIELDS = ["id", "title", "done", "priority", "due", "created"]


def export_csv(tasks):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for task in sort_tasks(tasks):
        writer.writerow({field: task.get(field, "") for field in EXPORT_FIELDS})
    return buf.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simple todo list")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="path to the JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a new task")
    p_add.add_argument("title", nargs="+")
    p_add.add_argument("-p", "--priority", choices=PRIORITY_ORDER, default="normal")
    p_add.add_argument("-d", "--due", type=date.fromisoformat, help="due date as YYYY-MM-DD")

    p_list = sub.add_parser("list", help="list all tasks")
    p_list.add_argument("-s", "--search", help="only show tasks containing this text")
    p_list.add_argument("--open", action="store_true", help="hide completed tasks")
    p_list.add_argument("--overdue", action="store_true", help="only show overdue tasks")

    p_done = sub.add_parser("done", help="mark a task as done")
    p_done.add_argument("id", type=int)

    p_rm = sub.add_parser("rm", help="remove a task")
    p_rm.add_argument("id", type=int)

    p_edit = sub.add_parser("edit", help="change a task's title")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("title", nargs="+")

    sub.add_parser("clear", help="remove all completed tasks")

    p_export = sub.add_parser("export", help="print tasks as Markdown or CSV")
    p_export.add_argument("-f", "--format", choices=["md", "csv"], default="md")
    p_export.add_argument("-o", "--output", type=Path, help="write to a file instead of stdout")

    args = parser.parse_args(argv)
    tasks = load_tasks(args.db)

    if args.command == "add":
        task = add_task(tasks, " ".join(args.title), args.priority, args.due)
        save_tasks(args.db, tasks)
        print(f"Added task {task['id']}: {task['title']}")
    elif args.command == "list":
        shown = filter_tasks(tasks, args.search, args.open)
        if args.overdue:
            shown = [t for t in shown if is_overdue(t)]
        if not shown:
            print("No tasks found." if tasks else "No tasks yet.")
        for task in sort_tasks(shown):
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

    elif args.command == "export":
        text = export_markdown(tasks) if args.format == "md" else export_csv(tasks)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
            print(f"Exported {len(tasks)} task(s) to {args.output}")
        else:
            print(text, end="")


if __name__ == "__main__":
    main()
