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
                "LIGHT_ON",
                "LIGHT_OFF",
                "SET_BRIGHTNESS",
                "AC_ON",
                "AC_OFF",
                "SET_TEMP",
                "FAN_ON",
                "FAN_OFF",
                "FAN_SPEED",
                "LOCK_DOOR",
                "UNLOCK_DOOR",
                "ADD_TASK",
                "REMOVE_TASK",
                "STATUS_REPORT",
            },
        )


if __name__ == "__main__":
    unittest.main()
