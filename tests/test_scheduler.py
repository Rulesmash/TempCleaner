"""Unit tests for Windows Task Scheduler argv builder and wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tempcleaner.platform_win.scheduler import (
    TASK_NAME,
    build_scheduled_command,
    build_schtasks_create_args,
    build_schtasks_delete_args,
    build_schtasks_query_args,
    install_schedule,
    remove_schedule,
    schedule_exists,
)


def test_build_daily_args():
    args = build_schtasks_create_args(
        task_name="TempCleaner Scheduled Clean",
        frequency="daily",
        time_hhmm="03:00",
        weekday=None,
        command=r"C:\Python\python.exe -m tempcleaner --scheduled",
    )
    assert "schtasks" in args[0] or args[0].endswith("schtasks")
    assert "/TN" in args
    assert "TempCleaner Scheduled Clean" in args
    assert "/SC" in args
    assert "DAILY" in args
    assert "/ST" in args
    assert "03:00" in args
    assert "/TR" in args
    assert r"C:\Python\python.exe -m tempcleaner --scheduled" in args
    assert "/F" in args
    # Daily must not require /D
    assert "/D" not in args


def test_build_weekly_args_includes_weekday():
    args = build_schtasks_create_args(
        task_name=TASK_NAME,
        frequency="weekly",
        time_hhmm="14:30",
        weekday="FRI",
        command="tempcleaner.exe --scheduled",
    )
    assert args[0] == "schtasks" or args[0].endswith("schtasks")
    assert "/SC" in args
    sc_idx = args.index("/SC")
    assert args[sc_idx + 1] == "WEEKLY"
    assert "/D" in args
    d_idx = args.index("/D")
    assert args[d_idx + 1] == "FRI"
    assert "14:30" in args
    tn_idx = args.index("/TN")
    assert args[tn_idx + 1] == TASK_NAME


def test_build_weekly_requires_weekday():
    with pytest.raises(ValueError, match="weekday"):
        build_schtasks_create_args(
            task_name=TASK_NAME,
            frequency="weekly",
            time_hhmm="09:00",
            weekday=None,
            command="x",
        )


def test_build_rejects_bad_frequency():
    with pytest.raises(ValueError, match="frequency"):
        build_schtasks_create_args(
            task_name=TASK_NAME,
            frequency="monthly",
            time_hhmm="03:00",
            weekday=None,
            command="x",
        )


def test_build_rejects_bad_time():
    with pytest.raises(ValueError, match="time"):
        build_schtasks_create_args(
            task_name=TASK_NAME,
            frequency="daily",
            time_hhmm="3am",
            weekday=None,
            command="x",
        )
    with pytest.raises(ValueError, match="time"):
        build_schtasks_create_args(
            task_name=TASK_NAME,
            frequency="daily",
            time_hhmm="25:00",
            weekday=None,
            command="x",
        )


def test_build_rejects_empty_command():
    with pytest.raises(ValueError, match="command"):
        build_schtasks_create_args(
            task_name=TASK_NAME,
            frequency="daily",
            time_hhmm="03:00",
            weekday=None,
            command="  ",
        )


def test_build_normalizes_frequency_and_weekday_case():
    args = build_schtasks_create_args(
        task_name=TASK_NAME,
        frequency="Weekly",
        time_hhmm="08:05",
        weekday="mon",
        command="cmd",
    )
    assert "WEEKLY" in args
    assert "MON" in args


def test_delete_and_query_args():
    delete = build_schtasks_delete_args(TASK_NAME)
    assert delete[0] == "schtasks" or delete[0].endswith("schtasks")
    assert "/Delete" in delete or "/DELETE" in [a.upper() for a in delete]
    assert TASK_NAME in delete
    assert "/F" in delete

    query = build_schtasks_query_args(TASK_NAME)
    assert query[0] == "schtasks" or query[0].endswith("schtasks")
    assert "/Query" in query or "/QUERY" in [a.upper() for a in query]
    assert TASK_NAME in query


def test_build_scheduled_command_module_mode():
    with patch("tempcleaner.platform_win.scheduler.sys") as mock_sys:
        mock_sys.frozen = False
        mock_sys.executable = r"C:\Python\python.exe"
        cmd = build_scheduled_command()
    assert "python.exe" in cmd
    assert "-m" in cmd
    assert "tempcleaner" in cmd
    assert "--scheduled" in cmd


def test_build_scheduled_command_frozen_mode():
    with patch("tempcleaner.platform_win.scheduler.sys") as mock_sys:
        mock_sys.frozen = True
        mock_sys.executable = r"C:\Apps\TempCleaner.exe"
        cmd = build_scheduled_command()
    assert "TempCleaner.exe" in cmd
    assert "--scheduled" in cmd
    assert "-m" not in cmd


def test_install_schedule_calls_subprocess_with_builder_args():
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "SUCCESS"
    fake.stderr = ""
    with patch(
        "tempcleaner.platform_win.scheduler.subprocess.run", return_value=fake
    ) as run:
        install_schedule(
            frequency="daily",
            time_hhmm="03:00",
            weekday=None,
            command=r"C:\Python\python.exe -m tempcleaner --scheduled",
        )
    run.assert_called_once()
    args = run.call_args[0][0]
    assert args[0] == "schtasks" or args[0].endswith("schtasks")
    assert "/TN" in args
    assert TASK_NAME in args
    assert "DAILY" in args
    kwargs = run.call_args[1]
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True
    assert kwargs.get("check") is False


def test_install_schedule_raises_on_failure():
    fake = MagicMock()
    fake.returncode = 1
    fake.stdout = ""
    fake.stderr = "Access is denied."
    with patch(
        "tempcleaner.platform_win.scheduler.subprocess.run", return_value=fake
    ), pytest.raises(RuntimeError, match="Access is denied"):
        install_schedule(
            frequency="daily",
            time_hhmm="03:00",
            weekday=None,
            command="x",
        )


def test_remove_schedule_calls_delete():
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "SUCCESS"
    fake.stderr = ""
    with patch(
        "tempcleaner.platform_win.scheduler.subprocess.run", return_value=fake
    ) as run:
        remove_schedule()
    args = run.call_args[0][0]
    assert "/Delete" in args or "/DELETE" in [a.upper() for a in args]
    assert TASK_NAME in args


def test_schedule_exists_true_false():
    ok = MagicMock()
    ok.returncode = 0
    ok.stdout = "TaskName"
    ok.stderr = ""
    missing = MagicMock()
    missing.returncode = 1
    missing.stdout = ""
    missing.stderr = "ERROR: The system cannot find the file specified."

    with patch(
        "tempcleaner.platform_win.scheduler.subprocess.run", return_value=ok
    ):
        assert schedule_exists() is True
    with patch(
        "tempcleaner.platform_win.scheduler.subprocess.run", return_value=missing
    ):
        assert schedule_exists() is False
