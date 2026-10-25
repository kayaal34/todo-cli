# todo-cli

A tiny command-line todo manager written in pure Python (no dependencies).
Tasks are stored in a JSON file (`~/.todo.json` by default).

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
python todo.py rm 2
python todo.py clear        # remove all completed tasks
```

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
