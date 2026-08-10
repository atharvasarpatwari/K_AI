import os
import tempfile
import time
import unittest

from keerthi.executive import ExecutiveOfficer


class TestPersistence(unittest.TestCase):
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            first = ExecutiveOfficer(state_file=state_file)
            first.parse_and_execute("[ACTION:ADD_TASK:Buy milk][ACTION:SET_TIMER:120]")

            second = ExecutiveOfficer(state_file=state_file)
            self.assertIn("Buy milk", second.state["tasks"])
            self.assertEqual(len(second.state["timers"]), 1)
            self.assertAlmostEqual(second.state["timers"][0]["due"], time.time() + 120, delta=5)

    def test_load_state_false_starts_from_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            first = ExecutiveOfficer(state_file=state_file)
            first.parse_and_execute("[ACTION:ADD_TASK:Buy milk]")

            fresh = ExecutiveOfficer(state_file=state_file, load_state=False)
            self.assertNotIn("Buy milk", fresh.state["tasks"])

    def test_missing_state_file_starts_from_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            officer = ExecutiveOfficer(state_file=os.path.join(d, "missing.json"))
            self.assertIsInstance(officer.state["tasks"], list)
            self.assertEqual(officer.state["timers"], [])

    def test_corrupt_state_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            with open(state_file, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            officer = ExecutiveOfficer(state_file=state_file)
            self.assertIsInstance(officer.state["tasks"], list)


if __name__ == "__main__":
    unittest.main()
