import os
import tempfile
import unittest
from unittest import mock

from keerthi.executive import ExecutiveOfficer


class TestExecutiveControl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.officer = ExecutiveOfficer(
            state_file=os.path.join(self.tmp.name, "state.json")
        )

    def tearDown(self):
        self.tmp.cleanup()

    # ---- Input automation ----

    def test_type_text(self):
        with mock.patch("keerthi.system.type_text", return_value="hello") as fn:
            executed = self.officer.parse_and_execute("[ACTION:TYPE_TEXT:hello]")
        fn.assert_called_once_with("hello")
        self.assertEqual(executed, ["Typed: hello"])

    def test_type_text_empty(self):
        executed = self.officer.parse_and_execute("[ACTION:TYPE_TEXT]")
        self.assertEqual(executed, ["No text given to type."])

    def test_press_keys(self):
        with mock.patch("keerthi.system.press_keys", return_value="ctrl+c") as fn:
            executed = self.officer.parse_and_execute("[ACTION:PRESS_KEYS:ctrl+c]")
        fn.assert_called_once_with("ctrl+c")
        self.assertEqual(executed, ["Pressed ctrl+c."])

    def test_move_mouse(self):
        with mock.patch("keerthi.system.move_mouse", return_value="(10, 20)") as fn:
            executed = self.officer.parse_and_execute("[ACTION:MOVE_MOUSE:10:20]")
        fn.assert_called_once_with(10, 20)
        self.assertEqual(executed, ["Moved cursor to (10, 20)."])

    def test_move_mouse_bad_args(self):
        executed = self.officer.parse_and_execute("[ACTION:MOVE_MOUSE:10]")
        self.assertEqual(
            executed, ["Please provide screen coordinates (e.g. MOVE_MOUSE:500:400)."]
        )

    def test_click_mouse_with_coordinates(self):
        with mock.patch(
            "keerthi.system.click_mouse", return_value="left click at (100, 200)"
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:CLICK_MOUSE:100:200]")
        fn.assert_called_once_with(100, 200, button="left")
        self.assertEqual(executed, ["Performed left click at (100, 200)."])

    def test_click_mouse_with_button(self):
        with mock.patch(
            "keerthi.system.click_mouse", return_value="right click"
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:CLICK_MOUSE:right]")
        fn.assert_called_once_with(None, None, button="right")
        self.assertEqual(executed, ["Performed right click."])

    def test_scroll_mouse(self):
        with mock.patch("keerthi.system.scroll_mouse", return_value="down 1") as fn:
            executed = self.officer.parse_and_execute("[ACTION:SCROLL_MOUSE:down]")
        fn.assert_called_once_with("down", 1)
        self.assertEqual(executed, ["Scrolled down 1."])

    # ---- Screenshots & screen analysis ----

    def test_take_screenshot(self):
        with mock.patch(
            "keerthi.system.take_screenshot", return_value="C:/shots/a.png"
        ):
            executed = self.officer.parse_and_execute("[ACTION:TAKE_SCREENSHOT]")
        self.assertEqual(executed, ["Screenshot saved to C:/shots/a.png."])

    def test_read_screen_with_vision_provider(self):
        self.officer.set_vision_provider(lambda path: f"Seen: {path}")
        with mock.patch(
            "keerthi.system.take_screenshot", return_value="C:/shots/a.png"
        ):
            executed = self.officer.parse_and_execute("[ACTION:READ_SCREEN]")
        self.assertEqual(executed, ["Seen: C:/shots/a.png"])

    def test_read_screen_without_vision_provider(self):
        with mock.patch(
            "keerthi.system.take_screenshot", return_value="C:/shots/a.png"
        ):
            executed = self.officer.parse_and_execute("[ACTION:READ_SCREEN]")
        self.assertEqual(executed, ["Screenshot saved to C:/shots/a.png."])

    def test_read_screen_screenshot_failed(self):
        with mock.patch("keerthi.system.take_screenshot", return_value=""):
            executed = self.officer.parse_and_execute("[ACTION:READ_SCREEN]")
        self.assertEqual(executed, ["Could not take a screenshot."])

    # ---- Power & display ----

    def test_shutdown(self):
        with mock.patch("keerthi.system.shutdown_system", return_value="Shutdown scheduled."):
            executed = self.officer.parse_and_execute("[ACTION:SHUTDOWN]")
        self.assertEqual(executed, ["Shutdown scheduled."])

    def test_restart(self):
        with mock.patch("keerthi.system.restart_system", return_value="Restart scheduled."):
            executed = self.officer.parse_and_execute("[ACTION:RESTART]")
        self.assertEqual(executed, ["Restart scheduled."])

    def test_sleep(self):
        with mock.patch("keerthi.system.sleep_system", return_value="Sleeping."):
            executed = self.officer.parse_and_execute("[ACTION:SLEEP]")
        self.assertEqual(executed, ["Sleeping."])

    def test_lock_screen(self):
        with mock.patch("keerthi.system.lock_screen", return_value="Locking the screen."):
            executed = self.officer.parse_and_execute("[ACTION:LOCK_SCREEN]")
        self.assertEqual(executed, ["Locking the screen."])

    def test_set_volume(self):
        with mock.patch("keerthi.system.set_volume", return_value="50%") as fn:
            executed = self.officer.parse_and_execute("[ACTION:SET_VOLUME:50]")
        fn.assert_called_once_with(50)
        self.assertEqual(executed, ["Volume set to 50%."])

    def test_set_volume_missing_arg(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_VOLUME]")
        self.assertEqual(
            executed, ["Please provide a volume percentage (e.g. SET_VOLUME:50)."]
        )

    def test_mute_on(self):
        with mock.patch("keerthi.system.set_mute", return_value="muted") as fn:
            executed = self.officer.parse_and_execute("[ACTION:MUTE]")
        fn.assert_called_once_with(True)
        self.assertEqual(executed, ["Volume muted."])

    def test_mute_off(self):
        with mock.patch("keerthi.system.set_mute", return_value="unmuted") as fn:
            executed = self.officer.parse_and_execute("[ACTION:MUTE:off]")
        fn.assert_called_once_with(False)
        self.assertEqual(executed, ["Volume unmuted."])

    def test_set_brightness(self):
        with mock.patch("keerthi.system.set_brightness", return_value="70%") as fn:
            executed = self.officer.parse_and_execute("[ACTION:SET_BRIGHTNESS:70]")
        fn.assert_called_once_with(70)
        self.assertEqual(executed, ["Brightness set to 70%."])

    # ---- Window management ----

    def test_list_windows(self):
        rows = [{"hwnd": 10, "title": "Notepad"}, {"hwnd": 20, "title": "Chrome"}]
        with mock.patch("keerthi.system.list_windows", return_value=rows):
            executed = self.officer.parse_and_execute("[ACTION:LIST_WINDOWS]")
        self.assertEqual(executed, ["Open windows: Notepad, Chrome."])

    def test_focus_window(self):
        with mock.patch(
            "keerthi.system.focus_window", return_value="Focused 'Notepad'."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:FOCUS_WINDOW:Notepad]")
        fn.assert_called_once_with("Notepad")
        self.assertEqual(executed, ["Focused 'Notepad'."])

    def test_close_window(self):
        with mock.patch(
            "keerthi.system.close_window", return_value="Closing 'Notepad'."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:CLOSE_WINDOW:Notepad]")
        fn.assert_called_once_with("Notepad")
        self.assertEqual(executed, ["Closing 'Notepad'."])

    # ---- Browser ----

    def test_open_url(self):
        with mock.patch(
            "keerthi.system.open_url", return_value="Opened https://x.com."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:OPEN_URL:https://x.com]")
        fn.assert_called_once_with("https://x.com")
        self.assertEqual(executed, ["Opened https://x.com."])

    def test_web_search(self):
        with mock.patch(
            "keerthi.system.web_search", return_value="Opened the search."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:WEB_SEARCH:best AI]")
        fn.assert_called_once_with("best AI")
        self.assertEqual(executed, ["Opened the search."])

    # ---- Safety gates ----

    def test_safety_gate_blocks_power_actions(self):
        with mock.patch("keerthi.system.shutdown_system") as shutdown:
            executed = self.officer.parse_and_execute(
                "[ACTION:SHUTDOWN]", confirm=lambda _: False
            )
        shutdown.assert_not_called()
        self.assertEqual(executed, [])

    def test_safety_gate_approves_power_actions(self):
        with mock.patch(
            "keerthi.system.shutdown_system", return_value="Shutdown scheduled."
        ) as shutdown:
            executed = self.officer.parse_and_execute(
                "[ACTION:SHUTDOWN]", confirm=lambda _: True
            )
        shutdown.assert_called_once()
        self.assertEqual(executed, ["Shutdown scheduled."])

    def test_safety_gate_blocks_input_injection(self):
        with mock.patch("keerthi.system.type_text") as typed:
            executed = self.officer.parse_and_execute(
                "[ACTION:TYPE_TEXT:hi]", confirm=lambda _: False
            )
        typed.assert_not_called()
        self.assertEqual(executed, [])

    def test_safety_gate_blocks_close_window(self):
        with mock.patch("keerthi.system.close_window") as closed:
            executed = self.officer.parse_and_execute(
                "[ACTION:CLOSE_WINDOW:Notepad]", confirm=lambda _: False
            )
        closed.assert_not_called()
        self.assertEqual(executed, [])


if __name__ == "__main__":
    unittest.main()
