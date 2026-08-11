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

    # ---- Macros ----

    def test_record_macro_starts_recorder(self):
        recorder = mock.MagicMock()
        recorder.start.return_value = True
        with mock.patch("keerthi.macros.MacroRecorder", return_value=recorder):
            executed = self.officer.parse_and_execute("[ACTION:MACRO_RECORD:demo]")
        self.assertEqual(
            executed, ["Recording macro 'demo' — say 'stop macro' when done."]
        )
        self.assertEqual(self.officer._recording_name, "demo")

    def test_record_macro_missing_name(self):
        executed = self.officer.parse_and_execute("[ACTION:MACRO_RECORD]")
        self.assertEqual(
            executed, ["Please name the macro to record (e.g. MACRO_RECORD:demo)."]
        )

    def test_stop_macro_saves(self):
        recorder = mock.MagicMock()
        recorder.stop.return_value = [{"t": 0.0, "type": "key", "key": "a"}]
        self.officer._recorder = recorder
        self.officer._recording_name = "demo"
        with mock.patch.object(
            self.officer._macro_store(), "save", return_value=True
        ) as save:
            executed = self.officer.parse_and_execute("[ACTION:MACRO_STOP]")
        save.assert_called_once_with("demo", [{"t": 0.0, "type": "key", "key": "a"}])
        self.assertEqual(executed, ["Macro 'demo' saved (1 events)."])

    def test_stop_macro_without_recording(self):
        executed = self.officer.parse_and_execute("[ACTION:MACRO_STOP]")
        self.assertEqual(executed, ["No macro recording is in progress."])

    def test_replay_macro(self):
        with mock.patch.object(
            self.officer._macro_store(), "load", return_value=[{"t": 0.0, "type": "move"}]
        ), mock.patch("keerthi.macros.replay_events", return_value=3):
            executed = self.officer.parse_and_execute("[ACTION:MACRO_REPLAY:demo]")
        self.assertEqual(executed, ["Replayed macro 'demo' (3 events)."])

    def test_replay_macro_unknown(self):
        with mock.patch.object(self.officer._macro_store(), "load", return_value=None):
            executed = self.officer.parse_and_execute("[ACTION:MACRO_REPLAY:nope]")
        self.assertEqual(executed, ["No macro named 'nope'."])

    def test_list_macros(self):
        with mock.patch.object(self.officer._macro_store(), "list", return_value=["a", "b"]):
            executed = self.officer.parse_and_execute("[ACTION:MACRO_LIST]")
        self.assertEqual(executed, ["Recorded macros: a, b."])

    def test_delete_macro(self):
        with mock.patch.object(
            self.officer._macro_store(), "delete", return_value=True
        ):
            executed = self.officer.parse_and_execute("[ACTION:MACRO_DELETE:demo]")
        self.assertEqual(executed, ["Deleted macro 'demo'."])

    # ---- Scheduled tasks ----

    def test_schedule_task_with_in_syntax(self):
        with mock.patch("keerthi.executive.time.time", return_value=1000.0):
            executed = self.officer.parse_and_execute(
                "[ACTION:SCHEDULE_TASK:notepad:in:5:minutes]"
            )
        self.assertEqual(len(self.officer.state["scheduled"]), 1)
        scheduled = self.officer.state["scheduled"][0]
        self.assertEqual(scheduled["command"], "notepad")
        self.assertAlmostEqual(scheduled["at"], 1000.0 + 300)
        self.assertIn("Scheduled 'notepad' to run in", executed[0])

    def test_schedule_task_with_hhmm(self):
        lt = __import__("time").struct_time((2026, 1, 1, 0, 0, 0, 3, 1, -1))
        with (
            mock.patch("keerthi.executive.time.time", return_value=1000.0),
            mock.patch("keerthi.executive.time.localtime", return_value=lt),
            mock.patch("keerthi.executive.time.mktime", return_value=1704067200.0),
        ):
            executed = self.officer.parse_and_execute(
                "[ACTION:SCHEDULE_TASK:echo hi:10:30]"
            )
        self.assertEqual(len(self.officer.state["scheduled"]), 1)
        self.assertEqual(self.officer.state["scheduled"][0]["command"], "echo hi")
        self.assertAlmostEqual(self.officer.state["scheduled"][0]["at"], 1704067200.0)
        self.assertIn("Scheduled 'echo hi'", executed[0])

    def test_schedule_task_bad_syntax(self):
        executed = self.officer.parse_and_execute("[ACTION:SCHEDULE_TASK:notepad]")
        self.assertEqual(
            executed,
            [
                "I couldn't parse that schedule. Use SCHEDULE_TASK:command:HH:MM "
                "or SCHEDULE_TASK:command:in:N:minutes."
            ],
        )

    def test_list_and_cancel_scheduled(self):
        self.officer.state["scheduled"] = [
            {"id": "x", "command": "notepad", "at": 9999999999.0}
        ]
        listed = self.officer.parse_and_execute("[ACTION:LIST_SCHEDULED]")
        self.assertIn("notepad", listed[0])
        cancelled = self.officer.parse_and_execute("[ACTION:CANCEL_SCHEDULED:0]")
        self.assertEqual(cancelled, ["Cancelled scheduled task 0 ('notepad')."])
        self.assertEqual(self.officer.state["scheduled"], [])

    def test_fire_due_scheduled_runs_command(self):
        self.officer.state["scheduled"] = [
            {"id": "x", "command": "echo done", "at": 1.0}
        ]
        with mock.patch(
            "keerthi.system.run_command", return_value="done"
        ) as run:
            messages = self.officer._fire_due_scheduled()
        run.assert_called_once_with("echo done")
        self.assertIn("Scheduled task 'echo done' ran: done", messages[0])
        self.assertEqual(self.officer.state["scheduled"], [])

    # ---- Software installation ----

    def test_install_app(self):
        with mock.patch(
            "keerthi.system.install_app", return_value="Installed 7zip."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:INSTALL_APP:7zip]")
        fn.assert_called_once_with("7zip")
        self.assertEqual(executed, ["Installed 7zip."])

    def test_install_app_missing_name(self):
        executed = self.officer.parse_and_execute("[ACTION:INSTALL_APP]")
        self.assertEqual(executed, ["Please name the app to install."])

    # ---- Window moves ----

    def test_move_window(self):
        with mock.patch(
            "keerthi.system.move_window", return_value="Moved 'Notepad' to (100, 100)."
        ) as fn:
            executed = self.officer.parse_and_execute(
                "[ACTION:MOVE_WINDOW:Notepad:100:100:800:600]"
            )
        fn.assert_called_once_with("Notepad", 100, 100, 800, 600)
        self.assertEqual(executed, ["Moved 'Notepad' to (100, 100)."])

    def test_move_window_without_size(self):
        with mock.patch(
            "keerthi.system.move_window", return_value="Moved 'Notepad' to (1, 2)."
        ) as fn:
            executed = self.officer.parse_and_execute("[ACTION:MOVE_WINDOW:Notepad:1:2]")
        fn.assert_called_once_with("Notepad", 1, 2, None, None)
        self.assertEqual(executed, ["Moved 'Notepad' to (1, 2)."])

    def test_move_window_bad_args(self):
        executed = self.officer.parse_and_execute("[ACTION:MOVE_WINDOW:Notepad]")
        self.assertEqual(
            executed,
            ["Please provide a window title and coordinates (e.g. MOVE_WINDOW:Notepad:100:100)."],
        )

    def test_move_window_to_monitor(self):
        with mock.patch(
            "keerthi.system.move_window_to_monitor", return_value="Moved 'Notepad' to monitor 1."
        ) as fn:
            executed = self.officer.parse_and_execute(
                "[ACTION:MOVE_WINDOW_TO_MONITOR:Notepad:1]"
            )
        fn.assert_called_once_with("Notepad", 1)
        self.assertEqual(executed, ["Moved 'Notepad' to monitor 1."])

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
