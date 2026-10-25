"""A tiny command-line todo manager that stores tasks in a JSON file."""

import argparse
import calendar
import csv
import io
import json
from datetime import date, datetime, timedelta
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


REPEAT_STEPS = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def normalize_tags(tags):
    """Lower-case, strip a leading # and drop duplicates, keeping order."""
    seen = []
    for tag in tags or []:
        tag = tag.strip().lstrip("#").lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def add_task(tasks, title, priority="normal", due=None, every=None, tags=None):
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": next_id,
        "title": title,
        "done": False,
        "priority": priority,
        "due": due.isoformat() if due else None,
        "every": every,
        "tags": normalize_tags(tags),
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    return task


def find_task(tasks, task_id):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"No task with id {task_id}")


def add_months(day, months):
    """The same day *months* later, clamped to the month's length (Jan 31 -> Feb 28)."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_due(due, every, today=None, anchor=None):
    """Next due date of a repeating task: the first repeat of *anchor* (the
    first due date, defaulting to *due*) after both *due* and today, so missed
    repeats don't pile up."""
    today = today or date.today()
    start = date.fromisoformat(anchor or due) if (anchor or due) else today
    after = max(today, date.fromisoformat(due)) if due else today
    steps = 1
    while True:
        # Count steps from the start date so a monthly task on the 31st
        # comes back to the 31st after a shorter month instead of drifting.
        if every == "monthly":
            result = add_months(start, steps)
        else:
            result = start + REPEAT_STEPS[every] * steps
        if result > after:
            return result
        steps += 1


def complete_task(tasks, task_id, today=None):
    """Mark a task done. A repeating task gets a fresh copy with the next due date,
    which is returned as the second value (None otherwise)."""
    task = find_task(tasks, task_id)
    task["done"] = True
    follow_up = None
    if task.get("every"):
        anchor = task.get("repeat_from") or task.get("due")
        follow_up = add_task(
            tasks, task["title"], task.get("priority", "normal"),
            next_due(task.get("due"), task["every"], today, anchor), task["every"],
            task.get("tags"),
        )
        follow_up["repeat_from"] = anchor
    return task, follow_up


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


def filter_tasks(tasks, search=None, only_open=False, tag=None):
    result = tasks
    if tag:
        wanted = normalize_tags([tag])[0]
        result = [t for t in result if wanted in t.get("tags", [])]
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
    if task.get("every"):
        line += f"  [repeats {task['every']}]"
    if task.get("tags"):
        line += "  " + " ".join(f"#{tag}" for tag in task["tags"])
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
        if task.get("every"):
            extras.append(f"repeats {task['every']}")
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"- [{mark}] {task['title']}{suffix}")
    return "\n".join(lines) + ("\n" if lines else "")


EXPORT_FIELDS = ["id", "title", "done", "priority", "due", "every", "created"]


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
    p_add.add_argument("-t", "--tag", action="append", dest="tags", default=[],
                       help="tag the task (repeatable): -t work -t urgent")
    p_add.add_argument("-e", "--every", choices=["daily", "weekly", "monthly"],
                       help="repeat the task: completing it adds the next occurrence")

    p_list = sub.add_parser("list", help="list all tasks")
    p_list.add_argument("-s", "--search", help="only show tasks containing this text")
    p_list.add_argument("--open", action="store_true", help="hide completed tasks")
    p_list.add_argument("--overdue", action="store_true", help="only show overdue tasks")
    p_list.add_argument("-t", "--tag", help="only show tasks with this tag")

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
        task = add_task(tasks, " ".join(args.title), args.priority, args.due, args.every, args.tags)
        save_tasks(args.db, tasks)
        print(f"Added task {task['id']}: {task['title']}")
    elif args.command == "list":
        shown = filter_tasks(tasks, args.search, args.open, args.tag)
        if args.overdue:
            shown = [t for t in shown if is_overdue(t)]
        if not shown:
            print("No tasks found." if tasks else "No tasks yet.")
        for task in sort_tasks(shown):
            print(format_task(task))
    elif args.command == "done":
        task, follow_up = complete_task(tasks, args.id)
        save_tasks(args.db, tasks)
        print(f"Completed: {task['title']}")
        if follow_up:
            print(f"Next {follow_up['every']} occurrence added as task {follow_up['id']}, due {follow_up['due']}")
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
