import tempfile
import unittest
from unittest import mock

from keerthi import macros


class TestMacroStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = f"{self._tmp.name}/macros.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        store = macros.MacroStore(self.path)
        events = [{"t": 0.0, "type": "move", "x": 10, "y": 20}]
        self.assertTrue(store.save("demo", events))
        self.assertEqual(store.load("demo"), events)

    def test_save_rejects_blank_or_empty(self):
        store = macros.MacroStore(self.path)
        self.assertFalse(store.save("", [{"t": 0.0, "type": "move", "x": 0, "y": 0}]))
        self.assertFalse(store.save("demo", []))

    def test_delete_and_list(self):
        store = macros.MacroStore(self.path)
        store.save("b", [{"t": 0.0, "type": "key", "key": "a"}])
        store.save("a", [{"t": 0.0, "type": "key", "key": "b"}])
        self.assertEqual(store.list(), ["a", "b"])
        self.assertTrue(store.delete("a"))
        self.assertFalse(store.delete("missing"))
        self.assertEqual(store.list(), ["b"])

    def test_load_missing_returns_none(self):
        store = macros.MacroStore(self.path)
        self.assertIsNone(store.load("nope"))

    def test_persists_across_instances(self):
        macros.MacroStore(self.path).save("x", [{"t": 0.0, "type": "key", "key": "a"}])
        store = macros.MacroStore(self.path)
        self.assertEqual(len(store.load("x")), 1)

    def test_corrupt_file_loads_empty(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not json")
        store = macros.MacroStore(self.path)
        self.assertEqual(store.list(), [])


class TestKeyMapping(unittest.TestCase):
    def test_key_name_uses_char(self):
        class Key:
            char = "a"

        self.assertEqual(macros._key_name(Key()), "a")

    def test_key_name_uses_name(self):
        class Key:
            char = None
            name = "enter"

        self.assertEqual(macros._key_name(Key()), "enter")

    def test_pyautogui_name_mapping(self):
        self.assertEqual(macros._pyautogui_name("ctrl_l"), "ctrl")
        self.assertEqual(macros._pyautogui_name("cmd"), "win")
        self.assertEqual(macros._pyautogui_name("page_up"), "pageup")
        self.assertEqual(macros._pyautogui_name("z"), "z")


class TestReplay(unittest.TestCase):
    def test_replay_returns_zero_without_pyautogui(self):
        with mock.patch.object(macros, "_load_pyautogui", return_value=None):
            self.assertEqual(macros.replay_events([{"t": 0.0, "type": "key", "key": "a"}]), 0)

    def test_replay_dispatches_events(self):
        pyautogui = mock.MagicMock()
        with mock.patch.object(macros, "_load_pyautogui", return_value=pyautogui):
            events = [
                {"t": 0.0, "type": "move", "x": 100, "y": 200},
                {"t": 0.1, "type": "click", "x": 100, "y": 200, "button": "left", "pressed": True},
                {"t": 0.2, "type": "key", "key": "enter"},
            ]
            count = macros.replay_events(events)
        self.assertEqual(count, 3)
        pyautogui.moveTo.assert_called_once_with(100, 200, duration=0)
        pyautogui.click.assert_called_once_with(100, 200, button="left")
        pyautogui.press.assert_called_once_with("enter")

    def test_replay_skips_failing_events(self):
        pyautogui = mock.MagicMock()
        pyautogui.press.side_effect = RuntimeError("boom")
        with mock.patch.object(macros, "_load_pyautogui", return_value=pyautogui):
            events = [{"t": 0.0, "type": "key", "key": "enter"}]
            self.assertEqual(macros.replay_events(events), 0)

    def test_replay_ignores_unreleased_clicks(self):
        pyautogui = mock.MagicMock()
        with mock.patch.object(macros, "_load_pyautogui", return_value=pyautogui):
            events = [
                {
                    "t": 0.0,
                    "type": "click",
                    "x": 1,
                    "y": 2,
                    "button": "left",
                    "pressed": False,
                }
            ]
            self.assertEqual(macros.replay_events(events), 1)
        pyautogui.click.assert_not_called()


class TestRecorder(unittest.TestCase):
    def test_start_returns_false_without_pynput(self):
        recorder = macros.MacroRecorder()
        with mock.patch("builtins.__import__", side_effect=ImportError("no pynput")):
            self.assertFalse(recorder.start())

    def test_start_and_stop(self):
        class FakeListener:
            def __init__(self, **_kwargs):
                self._stopped = False

            def start(self):
                pass

            def stop(self):
                self._stopped = True

            def join(self, timeout=1.0):
                pass

        recorder = macros.MacroRecorder()
        with mock.patch.dict(
            "sys.modules",
            {
                "pynput": mock.MagicMock(),
                "pynput.keyboard": mock.MagicMock(Listener=FakeListener),
                "pynput.mouse": mock.MagicMock(Listener=FakeListener),
            },
        ):
            self.assertTrue(recorder.start())
            recorder._on_move(5, 6)
            recorder._on_click(5, 6, mock.MagicMock(name="left"), True)
            recorder._on_scroll(5, 6, 0, -1)
            recorder._on_key(mock.MagicMock(char="x"))
        events = recorder.stop()
        self.assertFalse(recorder.active)
        kinds = [e["type"] for e in events]
        self.assertIn("move", kinds)
        self.assertIn("click", kinds)
        self.assertIn("scroll", kinds)
        self.assertIn("key", kinds)
        self.assertTrue(all(e["t"] >= 0 for e in events))

    def test_events_are_timestamp_ordered(self):
        recorder = macros.MacroRecorder()
        recorder._started = 0.0
        recorder._on_move(1, 2)
        recorder._on_key(mock.MagicMock(char="z"))
        events = recorder.stop()
        self.assertEqual(len(events), 2)
        self.assertLessEqual(events[0]["t"], events[1]["t"])


if __name__ == "__main__":
    unittest.main()
