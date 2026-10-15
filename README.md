# todo-cli

A tiny command-line todo manager written in pure Python (no dependencies).
Tasks are stored in a JSON file (`~/.todo.json` by default).

## Usage

```bash
python todo.py add Buy milk
python todo.py add -p high Pay rent   # priorities: high, normal, low
python todo.py list
python todo.py list --search milk --open
python todo.py edit 1 Buy oat milk
python todo.py done 1
python todo.py rm 2
python todo.py clear        # remove all completed tasks
```

Use `--db path/to/file.json` to keep separate lists.

## Running tests

```bash
pip install pytest
pytest
```
