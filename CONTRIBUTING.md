# Contributing to TempCleaner

Thanks for helping improve TempCleaner. This document covers setup, quality bars, and project norms for **v2.0**.

## Project constraints (do not break these)

| Rule | Detail |
|------|--------|
| Platform | **Windows only** |
| Python | **3.10+** |
| Runtime deps | **stdlib only** — do not add `ttkbootstrap`, `send2trash`, `pystray`, etc. for runtime |
| Delete model | **Permanent delete** after GUI confirm or CLI `--yes`; dry-run must keep working |
| Path safety | Only allowlisted roots; never delete drive roots or user profile root |
| Errors | Catch `OSError` / `PermissionError` (and subclasses); **no bare `except:`** |
| Tests | Use `tmp_path` only — **never** delete real `C:\Windows\*` in tests |
| UI | Modern **ttk**, not PNG button layouts |
| License | Keep **GNU GPLv3** |

Explicit non-goals for 2.0 (do not land in PRs without design agreement): system tray, Recycle Bin soft-delete, browser caches, custom arbitrary paths, auto-install of updates.

## Development setup

```powershell
git clone https://github.com/Rulesmash/TempCleaner.git
cd TempCleaner

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -e ".[dev]"
```

Package layout: source under `src/tempcleaner/` (see `pyproject.toml`).

## Running the app

```powershell
python -m tempcleaner
python -m tempcleaner --version
python -m tempcleaner --scan --targets user_temp
```

## Tests and lint

```powershell
pytest -q
ruff check src tests
```

- Prefer focused unit tests for `core/`, `config/`, and mocked `platform_win/`.
- Do not require a full GUI E2E for every change; CI targets core/logic.
- Keep test deletes confined to pytest `tmp_path` fixtures.

## Code organization

```text
src/tempcleaner/
  app.py              # CLI + entry
  core/               # engine, targets, safety, models (no Tkinter)
  config/             # defaults + settings JSON
  platform_win/       # admin, paths, scheduler, updates
  ui/                 # ttk windows and tabs
  util/               # logging, sizing helpers
```

- **core** must not import Tkinter.
- Windows APIs stay in **platform_win** so tests can mock them.
- UI calls engine/settings; it should not reimplement delete logic.

## Pull requests

1. Branch from the active development branch (e.g. `feature/v2-revamp` or `main` as directed).
2. Keep changes focused; match existing style (ruff line length 100, Python 3.10 typing).
3. Add/adjust tests for behavior changes in engine, safety, settings, CLI, scheduler builders.
4. Update docs if user-facing behavior changes (README, user-guide, CHANGELOG).
5. Do not force-push shared history unless maintainers explicitly request it.
6. Ensure `pytest -q` and `ruff check src tests` pass on Windows.

## Commit messages

Prefer short, imperative subjects, e.g.:

- `feat: …`
- `fix: …`
- `docs: …`
- `test: …`
- `chore: …`

## Reporting bugs

Use [GitHub Issues](https://github.com/Rulesmash/TempCleaner/issues). Include:

- Windows version
- TempCleaner version (`python -m tempcleaner --version`)
- Whether the process was elevated
- Steps to reproduce
- Relevant log lines from `%AppData%\TempCleaner\logs\`

Security-sensitive reports: see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the same **GNU GPLv3** terms as the project (`LICENSE`).
