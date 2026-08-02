"""Windows elevation: detect admin and re-launch elevated via UAC."""

from __future__ import annotations

import ctypes
import subprocess
import sys


def is_admin() -> bool:
    """Return True if the current process token has admin rights.

    Uses ``shell32.IsUserAnAdmin()``. Returns False on API failure.
    """
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def relaunch_as_admin(argv: list[str] | None = None) -> None:
    """Start an elevated copy of this process via ``ShellExecuteW`` ``runas``.

    Does **not** exit the current process; the caller should exit after a
    successful return so only the elevated instance remains.

    Args:
        argv: Command-line arguments as for ``sys.argv``. When ``None``,
            uses ``sys.argv``. For a normal Python run this is the script
            path plus options (passed as parameters to ``sys.executable``).
            For a frozen executable, only remaining args after the exe.

    Raises:
        OSError: If not on Windows, or if ShellExecuteW returns an error
            code (including UAC cancel, typically code 1223 mapped as <= 32).
    """
    if sys.platform != "win32":
        raise OSError("Admin elevation is only supported on Windows")

    if argv is None:
        argv = list(sys.argv)

    executable = sys.executable
    if getattr(sys, "frozen", False):
        # PyInstaller / frozen: executable is the app; drop argv[0] (exe path).
        params_list = argv[1:] if argv else []
    else:
        # Interpreter: pass script/module path and options as parameters.
        params_list = list(argv)

    params = subprocess.list2cmdline(params_list) if params_list else None

    # ShellExecuteW: return value > 32 means success; <= 32 is an error code.
    rc = int(
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            params,
            None,
            1,  # SW_SHOWNORMAL
        )
    )
    if rc <= 32:
        raise OSError(f"ShellExecuteW runas failed with code {rc}")
