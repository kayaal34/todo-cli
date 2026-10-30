# todo-cli

A tiny command-line todo manager written in pure Python (no dependencies).
Tasks are stored in a JSON file (`~/.todo.json` by default).

## Install

```bash
pip install git+https://github.com/kayaal34/todo-cli
todo add Buy milk
```

Or run it straight from a checkout with `python todo.py ...` (no dependencies).

## Usage

```bash
python todo.py add Buy milk
python todo.py add -p high Pay rent   # priorities: high, normal, low
python todo.py add -d 2026-11-01 Renew passport   # due date
python todo.py list --overdue
python todo.py add -e weekly -d 2026-11-02 Water plants   # repeats: daily, weekly, monthly
python todo.py list
python todo.py list --search milk --open
python todo.py edit 1 Buy oat milk
python todo.py done 1
python todo.py reopen 1     # undo "done" (also drops the next occurrence of a repeating task)
python todo.py set 1 -p high -d 2026-11-05 -t home   # or --no-due
python todo.py snooze 1 3   # due 3 days later (default 1), from today if overdue
python todo.py rm 2
python todo.py clear        # remove all completed tasks
```

### Agenda

```
$ todo agenda
Overdue
  [ ]   3 ! Renew passport  (due 2026-10-20, OVERDUE)
Tue 2026-10-27
  [ ]   5   Dentist  (due 2026-10-27)
Fri 2026-10-30
  [ ]   7   Water plants  (due 2026-10-30)  [repeats weekly]
```

Shows open tasks due in the next 7 days (`-n` to change), grouped by day, with overdue ones first.

### Stats

```
$ todo stats
Open: 4  Done: 12  Overdue: 1
Completed in the last 7 day(s):
  2026-10-20    2  ##
  2026-10-21    0
  ...
```

Completion dates are recorded from now on; tasks completed before this version don't count.

### Tags

```bash
python todo.py add -t work -t urgent Fix the login bug
python todo.py list --tag work
python todo.py tags          # tags of open tasks with counts (--all includes done ones)
```

Tags are case-insensitive and a leading `#` is ignored, so `Work`, `work` and `#work` are the same tag.

### Repeating tasks

`add --every daily|weekly|monthly` makes a task repeat. Completing it with `done`
adds the next occurrence with the next due date. Missed repeats are skipped
rather than piling up, and a monthly task due on the 31st stays on the last day
of shorter months (Aug 31 -> Sep 30 -> Oct 31).

### Export

```bash
python todo.py export                 # Markdown checklist
python todo.py export -f csv -o tasks.csv
```

Use `--db path/to/file.json` to keep separate lists.

## Running tests

```bash
pip install pytest
pytest
```
