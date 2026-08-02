"""CLI entrypoint tests for tempcleaner.app.main."""

from tempcleaner.app import main


def test_version_exit_zero(capsys):
    assert main(["--version"]) == 0
    assert "2.0.0" in capsys.readouterr().out


def test_clean_requires_yes():
    assert main(["--clean"]) == 2
