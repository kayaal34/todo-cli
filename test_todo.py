from datetime import date

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
    assert rows[0] == "id,title,done,priority,due,every,tags,created"
    assert rows[1].startswith("1,Write report,False,high,2026-11-01,,,")
    assert todo.export_markdown([]) == ""


def test_cli_export_to_file(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    out = tmp_path / "tasks.md"
    todo.main(["--db", str(db), "add", "Plan trip"])
    todo.main(["--db", str(db), "export", "-o", str(out)])
    assert out.read_text(encoding="utf-8") == "- [ ] Plan trip\n"
    todo.main(["--db", str(db), "export", "--format", "csv"])
    assert "Plan trip" in capsys.readouterr().out


def test_next_due():
    from datetime import date

    today = date(2026, 10, 24)
    assert todo.next_due("2026-10-25", "daily", today) == date(2026, 10, 26)
    assert todo.next_due("2026-10-20", "weekly", today) == date(2026, 10, 27)  # missed one is skipped
    assert todo.next_due(None, "weekly", today) == date(2026, 10, 31)
    assert todo.next_due("2026-01-31", "monthly", date(2026, 1, 1)) == date(2026, 2, 28)
    assert todo.next_due("2026-12-15", "monthly", today) == date(2027, 1, 15)
    assert todo.next_due("2026-08-31", "monthly", today) == date(2026, 10, 31)


def test_completing_repeating_task_adds_next_occurrence():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Pay rent", "high", date(2026, 11, 1), "monthly")
    done, follow_up = todo.complete_task(tasks, 1, today=date(2026, 10, 30))
    assert done["done"] is True
    assert follow_up == tasks[1]
    assert (follow_up["title"], follow_up["priority"], follow_up["due"], follow_up["every"]) == (
        "Pay rent", "high", "2026-12-01", "monthly")
    assert "[repeats monthly]" in todo.format_task(follow_up)
    assert todo.complete_task(tasks, 2, today=date(2026, 10, 30))[1]["due"] == "2027-01-01"


def test_completing_normal_task_adds_nothing():
    tasks = []
    todo.add_task(tasks, "once")
    assert todo.complete_task(tasks, 1)[1] is None
    assert len(tasks) == 1


def test_monthly_task_on_the_31st_does_not_drift():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Report", due=date(2026, 8, 31), every="monthly")
    dues = []
    for task_id, today in [(1, date(2026, 8, 31)), (2, date(2026, 9, 30)), (3, date(2026, 10, 31))]:
        dues.append(todo.complete_task(tasks, task_id, today=today)[1]["due"])
    assert dues == ["2026-09-30", "2026-10-31", "2026-11-30"]


def test_export_shows_repeat():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Water plants", due=date(2026, 11, 1), every="weekly")
    assert todo.export_markdown(tasks) == "- [ ] Water plants (due 2026-11-01, repeats weekly)\n"
    assert ",weekly," in todo.export_csv(tasks).splitlines()[1]


def test_tags_are_normalized_and_filterable():
    tasks = []
    todo.add_task(tasks, "Write report", tags=["Work", "#urgent", "work"])
    todo.add_task(tasks, "Buy milk", tags=["home"])
    assert tasks[0]["tags"] == ["work", "urgent"]
    assert [t["title"] for t in todo.filter_tasks(tasks, tag="#WORK")] == ["Write report"]
    assert todo.filter_tasks(tasks, tag="garden") == []
    assert todo.format_task(tasks[0]).endswith("#work #urgent")


def test_old_tasks_without_tags_still_work():
    old = {"id": 1, "title": "legacy", "done": False}
    assert todo.filter_tasks([old], tag="work") == []
    assert "#" not in todo.format_task(old)


def test_repeating_task_keeps_tags():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Standup", due=date(2026, 10, 26), every="daily", tags=["work"])
    assert todo.complete_task(tasks, 1, today=date(2026, 10, 26))[1]["tags"] == ["work"]


def test_cli_tags(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    todo.main(["--db", str(db), "add", "-t", "work", "-t", "deep", "Write", "report"])
    todo.main(["--db", str(db), "add", "Buy", "milk"])
    capsys.readouterr()
    todo.main(["--db", str(db), "list", "--tag", "work"])
    out = capsys.readouterr().out
    assert "Write report" in out and "#work #deep" in out and "Buy milk" not in out


def test_tag_counts_and_export():
    tasks = []
    todo.add_task(tasks, "a", tags=["work", "urgent"])
    todo.add_task(tasks, "b", tags=["work"])
    todo.add_task(tasks, "c", tags=["home"])
    todo.complete_task(tasks, 3)
    assert todo.tag_counts(tasks) == [("work", 2), ("urgent", 1)]
    assert todo.tag_counts(tasks, only_open=False) == [("work", 2), ("home", 1), ("urgent", 1)]
    assert "- [ ] a (#work, #urgent)" in todo.export_markdown(tasks)
    assert ",work urgent," in todo.export_csv(tasks)


def test_reopen_task():
    tasks = []
    todo.add_task(tasks, "Write report")
    todo.complete_task(tasks, 1)
    task, removed = todo.reopen_task(tasks, 1)
    assert task["done"] is False and removed is None
    with pytest.raises(SystemExit):
        todo.reopen_task(tasks, 1)


def test_reopen_repeating_task_removes_its_next_occurrence():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Standup", due=date(2026, 10, 26), every="daily")
    todo.complete_task(tasks, 1, today=date(2026, 10, 26))
    assert [t["id"] for t in tasks] == [1, 2]
    task, removed = todo.reopen_task(tasks, 1)
    assert removed["id"] == 2 and [t["id"] for t in tasks] == [1]
    assert "follow_up" not in task


def test_reopen_keeps_next_occurrence_that_was_already_done():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "Standup", due=date(2026, 10, 26), every="daily")
    todo.complete_task(tasks, 1, today=date(2026, 10, 26))
    todo.complete_task(tasks, 2, today=date(2026, 10, 27))
    assert todo.reopen_task(tasks, 1)[1] is None
    assert [t["id"] for t in tasks] == [1, 2, 3]


def test_completion_date_is_recorded_and_cleared_on_reopen():
    from datetime import date

    tasks = []
    todo.add_task(tasks, "a")
    todo.complete_task(tasks, 1, today=date(2026, 10, 26))
    assert tasks[0]["completed"] == "2026-10-26"
    todo.reopen_task(tasks, 1)
    assert "completed" not in tasks[0]


def test_stats():
    from datetime import date

    today = date(2026, 10, 26)
    tasks = []
    for title in "abcde":
        todo.add_task(tasks, title)
    todo.add_task(tasks, "late", due=date(2026, 10, 20))
    todo.complete_task(tasks, 1, today=date(2026, 10, 26))
    todo.complete_task(tasks, 2, today=date(2026, 10, 26))
    todo.complete_task(tasks, 3, today=date(2026, 10, 24))
    todo.complete_task(tasks, 4, today=date(2026, 10, 1))  # outside the window
    result = todo.stats(tasks, today, days=3)
    assert (result["open"], result["done"], result["overdue"]) == (2, 4, 1)
    assert result["completed_per_day"] == {"2026-10-24": 1, "2026-10-25": 0, "2026-10-26": 2}


def test_cli_stats(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    todo.main(["--db", str(db), "add", "one"])
    todo.main(["--db", str(db), "add", "two"])
    todo.main(["--db", str(db), "done", "1"])
    capsys.readouterr()
    todo.main(["--db", str(db), "stats", "-n", "2"])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Open: 1  Done: 1  Overdue: 0"
    assert out[-1].endswith("1  #")
    with pytest.raises(SystemExit):
        todo.main(["--db", str(db), "stats", "-n", "0"])


def test_agenda_groups_by_day():
    from datetime import date

    today = date(2026, 10, 27)
    tasks = []
    todo.add_task(tasks, "late", due=date(2026, 10, 20))
    todo.add_task(tasks, "today low", "low", date(2026, 10, 27))
    todo.add_task(tasks, "today high", "high", date(2026, 10, 27))
    todo.add_task(tasks, "friday", due=date(2026, 10, 30))
    todo.add_task(tasks, "next month", due=date(2026, 11, 20))
    todo.add_task(tasks, "no date")
    todo.add_task(tasks, "done", due=date(2026, 10, 28))
    todo.complete_task(tasks, 7, today=today)
    result = todo.agenda(tasks, today, days=7)
    assert list(result) == ["overdue", "2026-10-27", "2026-10-30"]
    assert [t["title"] for t in result["2026-10-27"]] == ["today high", "today low"]
    assert [t["title"] for t in result["overdue"]] == ["late"]


def test_cli_agenda(tmp_path, capsys):
    from datetime import date, timedelta

    db = tmp_path / "tasks.json"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    todo.main(["--db", str(db), "agenda"])
    assert "Nothing due in the next 7 day(s)." in capsys.readouterr().out
    todo.main(["--db", str(db), "add", "-d", tomorrow, "Dentist"])
    capsys.readouterr()
    todo.main(["--db", str(db), "agenda", "-n", "3"])
    out = capsys.readouterr().out.splitlines()
    assert out[0].endswith(tomorrow) and "Dentist" in out[1]


def test_snooze_moves_a_future_due_date():
    tasks = []
    todo.add_task(tasks, "a", due=date(2026, 11, 10))
    todo.snooze_task(tasks, 1, days=3, today=date(2026, 11, 1))
    assert tasks[0]["due"] == "2026-11-13"


def test_snooze_counts_from_today_when_overdue_or_undated():
    tasks = []
    todo.add_task(tasks, "late", due=date(2026, 10, 1))
    todo.add_task(tasks, "undated")
    todo.snooze_task(tasks, 1, today=date(2026, 11, 1))
    todo.snooze_task(tasks, 2, days=2, today=date(2026, 11, 1))
    assert [t["due"] for t in tasks] == ["2026-11-02", "2026-11-03"]


def test_snooze_keeps_a_repeating_task_on_its_schedule():
    tasks = []
    todo.add_task(tasks, "rent", due=date(2026, 10, 31), every="monthly")
    todo.snooze_task(tasks, 1, days=5, today=date(2026, 10, 30))
    _, follow_up = todo.complete_task(tasks, 1, today=date(2026, 11, 5))
    assert follow_up["due"] == "2026-11-30"


def test_snooze_rejects_a_done_task():
    tasks = []
    todo.add_task(tasks, "a")
    todo.complete_task(tasks, 1)
    with pytest.raises(SystemExit):
        todo.snooze_task(tasks, 1)


def test_snooze_command(tmp_path, capsys):
    db = tmp_path / "tasks.json"
    todo.main(["--db", str(db), "add", "-d", "2999-01-01", "Far away"])
    capsys.readouterr()
    todo.main(["--db", str(db), "snooze", "1", "2"])
    assert "2999-01-03" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        todo.main(["--db", str(db), "snooze", "1", "0"])
