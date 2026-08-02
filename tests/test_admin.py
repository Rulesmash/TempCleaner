import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_is_admin_returns_bool():
    from tempcleaner.platform_win.admin import is_admin

    assert isinstance(is_admin(), bool)
