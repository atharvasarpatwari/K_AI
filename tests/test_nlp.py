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
            },
        )

    def test_manifest_marks_safety_intents(self):
        manifest = get_nlp_manifest()
        self.assertIn("[ACTION:KILL_PROCESS] [SAFETY]", manifest)
        self.assertIn("[ACTION:RUN_COMMAND] [SAFETY]", manifest)
        self.assertIn("[ACTION:REMOVE_TASK] [SAFETY]", manifest)
        self.assertIn("confirm", manifest)


if __name__ == "__main__":
    unittest.main()
