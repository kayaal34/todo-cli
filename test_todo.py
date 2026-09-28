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
