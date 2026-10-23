import pytest

import todo


def test_add_assigns_incrementing_ids():
    tasks = []
    first = todo.add_task(tasks, "first")
    second = todo.add_task(tasks, "second")
    assert (first["id"], second["id"]) == (1, 2)
    assert not first["done"]


def test_complete_and_clear():
    tasks = []
    todo.add_task(tasks, "a")
    todo.add_task(tasks, "b")
    todo.complete_task(tasks, 1)
    assert todo.clear_done(tasks) == 1
    assert [t["title"] for t in tasks] == ["b"]


def test_remove_unknown_id_exits():
    with pytest.raises(SystemExit):
        todo.remove_task([], 42)


def test_save_and_load_roundtrip(tmp_path):
    db = tmp_path / "tasks.json"
    tasks = []
    todo.add_task(tasks, "çay demle")
    todo.save_tasks(db, tasks)
    assert todo.load_tasks(db) == tasks


def test_cli_add_and_list(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    todo.main(["--db", str(db), "add", "write", "tests"])
    todo.main(["--db", str(db), "list"])
    out = capsys.readouterr().out
    assert "write tests" in out


def test_sort_puts_high_priority_open_tasks_first():
    tasks = []
    todo.add_task(tasks, "low", "low")
    todo.add_task(tasks, "urgent", "high")
    todo.add_task(tasks, "finished", "high")
    todo.complete_task(tasks, 3)
    assert [t["title"] for t in todo.sort_tasks(tasks)] == ["urgent", "low", "finished"]


def test_rename_task():
    tasks = []
    todo.add_task(tasks, "old")
    todo.rename_task(tasks, 1, "new")
    assert tasks[0]["title"] == "new"


def test_filter_by_search_and_open():
    tasks = []
    todo.add_task(tasks, "Buy milk")
    todo.add_task(tasks, "buy bread")
    todo.add_task(tasks, "Call mom")
    todo.complete_task(tasks, 2)
    assert [t["id"] for t in todo.filter_tasks(tasks, "BUY")] == [1, 2]
    assert [t["id"] for t in todo.filter_tasks(tasks, "buy", only_open=True)] == [1]


def test_due_date_and_overdue():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "pay rent", due=date(2026, 10, 1))
    todo.add_task(tasks, "later", due=date(2026, 12, 1))
    todo.add_task(tasks, "no date")
    today = date(2026, 10, 19)
    assert [todo.is_overdue(t, today) for t in tasks] == [True, False, False]
    assert "OVERDUE" in todo.format_task(tasks[0], today)
    todo.complete_task(tasks, 1)
    assert not todo.is_overdue(tasks[0], today)


def test_export_markdown_and_csv():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Write report", "high", date(2026, 11, 1))
    todo.add_task(tasks, "Buy milk")
    todo.complete_task(tasks, 2)
    assert todo.export_markdown(tasks).splitlines() == [
        "- [ ] Write report (high, due 2026-11-01)",
        "- [x] Buy milk",
    ]
    rows = todo.export_csv(tasks).splitlines()
    assert rows[0] == "id,title,done,priority,due,created"
    assert rows[1].startswith("1,Write report,False,high,2026-11-01,")
    assert todo.export_markdown([]) == ""


def test_cli_export_to_file(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    out = tmp_path / "tasks.md"
    todo.main(["--db", str(db), "add", "Plan trip"])
    todo.main(["--db", str(db), "export", "-o", str(out)])
    assert out.read_text(encoding="utf-8") == "- [ ] Plan trip\n"
    todo.main(["--db", str(db), "export", "--format", "csv"])
    assert "Plan trip" in capsys.readouterr().out
