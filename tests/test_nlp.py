import unittest

from keerthi.nlp import COMMAND_INTENTS, get_nlp_manifest


class TestNlpManifest(unittest.TestCase):
    def test_manifest_contains_all_intents(self):
        manifest = get_nlp_manifest()
        for intent in COMMAND_INTENTS:
            self.assertIn(f"[ACTION:{intent}]", manifest)

    def test_manifest_is_a_nonempty_string(self):
        self.assertIsInstance(get_nlp_manifest(), str)
        self.assertTrue(get_nlp_manifest().strip())

    def test_command_intents_keys(self):
        self.assertEqual(
            set(COMMAND_INTENTS),
            {
                "SYSTEM_STATUS",
                "CPU_USAGE",
                "MEMORY_USAGE",
                "DISK_USAGE",
                "BATTERY_STATUS",
                "LIST_PROCESSES",
                "KILL_PROCESS",
                "OPEN_APP",
                "RUN_COMMAND",
                "FILE_LIST",
                "OPEN_FILE",
                "RESET_STATE",
                "SET_TIMER",
                "CANCEL_TIMER",
                "CHECK_TIMERS",
                "ADD_TASK",
                "REMOVE_TASK",
                "STATUS_REPORT",
                "WEATHER_REPORT",
                "TYPE_TEXT",
                "PRESS_KEYS",
                "MOVE_MOUSE",
                "CLICK_MOUSE",
                "SCROLL_MOUSE",
                "TAKE_SCREENSHOT",
                "READ_SCREEN",
                "SHUTDOWN",
                "RESTART",
                "SLEEP",
                "LOCK_SCREEN",
                "SET_VOLUME",
                "MUTE",
                "SET_BRIGHTNESS",
                "LIST_WINDOWS",
                "FOCUS_WINDOW",
                "MINIMIZE_WINDOW",
                "MAXIMIZE_WINDOW",
                "CLOSE_WINDOW",
                "OPEN_URL",
                "WEB_SEARCH",
                "SAVE_FACT",
                "LIST_FACTS",
                "MACRO_RECORD",
                "MACRO_STOP",
                "MACRO_REPLAY",
                "MACRO_LIST",
                "MACRO_DELETE",
                "SCHEDULE_TASK",
                "CANCEL_SCHEDULED",
                "LIST_SCHEDULED",
                "INSTALL_APP",
                "MOVE_WINDOW",
                "MOVE_WINDOW_TO_MONITOR",
            },
        )

    def test_manifest_marks_safety_intents(self):
        manifest = get_nlp_manifest()
        self.assertIn("[ACTION:KILL_PROCESS] [SAFETY]", manifest)
        self.assertIn("[ACTION:RUN_COMMAND] [SAFETY]", manifest)
        self.assertIn("[ACTION:REMOVE_TASK] [SAFETY]", manifest)
        self.assertIn("[ACTION:TYPE_TEXT] [SAFETY]", manifest)
        self.assertIn("[ACTION:SHUTDOWN] [SAFETY]", manifest)
        self.assertIn("[ACTION:CLOSE_WINDOW] [SAFETY]", manifest)
        self.assertNotIn("[ACTION:TAKE_SCREENSHOT] [SAFETY]", manifest)
        self.assertNotIn("[ACTION:OPEN_URL] [SAFETY]", manifest)
        self.assertIn("[ACTION:MACRO_REPLAY] [SAFETY]", manifest)
        self.assertNotIn("[ACTION:MACRO_LIST] [SAFETY]", manifest)
        self.assertIn("[ACTION:SCHEDULE_TASK] [SAFETY]", manifest)
        self.assertIn("[ACTION:INSTALL_APP] [SAFETY]", manifest)
        self.assertIn("confirm", manifest)


if __name__ == "__main__":
    unittest.main()
