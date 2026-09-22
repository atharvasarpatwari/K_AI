import os
import sys
import unittest
from unittest import mock

import main


class TestEnableUnicodeConsole(unittest.TestCase):
    def test_reconfigures_stdout_and_stderr_to_utf8_on_windows(self):
        with (
            mock.patch.object(os, "name", "nt"),
            mock.patch.object(os, "system") as mock_system,
            mock.patch.object(sys.stdout, "reconfigure") as mock_out,
            mock.patch.object(sys.stderr, "reconfigure") as mock_err,
        ):
            main._enable_unicode_console()

        mock_system.assert_called_once()
        mock_out.assert_called_once_with(encoding="utf-8", errors="replace")
        mock_err.assert_called_once_with(encoding="utf-8", errors="replace")

    def test_noop_on_non_windows(self):
        with (
            mock.patch.object(os, "name", "posix"),
            mock.patch.object(os, "system") as mock_system,
            mock.patch.object(sys.stdout, "reconfigure") as mock_out,
        ):
            main._enable_unicode_console()

        mock_system.assert_not_called()
        mock_out.assert_not_called()


if __name__ == "__main__":
    unittest.main()
