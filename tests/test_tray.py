import unittest
from unittest import mock

from keerthi import tray


class TestTray(unittest.TestCase):
    def test_start_tray_returns_false_without_pystray(self):
        with mock.patch.object(tray, "_load_pystray", return_value=None):
            self.assertFalse(tray.start_tray())

    def test_start_tray_spawns_icon(self):
        icon = mock.MagicMock()
        pystray = mock.MagicMock()
        pystray.Icon.return_value = icon
        with mock.patch.object(tray, "_load_pystray", return_value=pystray):
            started = tray.start_tray(on_quit=lambda: None, dashboard_url="http://x")
        self.assertTrue(started)
        pystray.Icon.assert_called_once()
        self.assertEqual(icon.run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
