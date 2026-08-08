import os
import tempfile
import unittest

from keerthi.executive import ExecutiveOfficer


class TestPersistence(unittest.TestCase):
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            first = ExecutiveOfficer(state_file=state_file)
            first.parse_and_execute("[ACTION:LIGHT_ON][ACTION:ADD_TASK:Buy milk]")

            second = ExecutiveOfficer(state_file=state_file)
            self.assertEqual(second.state["devices"]["living_room_light"]["status"], "on")
            self.assertIn("Buy milk", second.state["tasks"])

    def test_load_state_false_starts_from_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            first = ExecutiveOfficer(state_file=state_file)
            first.parse_and_execute("[ACTION:LIGHT_ON]")

            fresh = ExecutiveOfficer(state_file=state_file, load_state=False)
            self.assertEqual(fresh.state["devices"]["living_room_light"]["status"], "off")

    def test_missing_state_file_starts_from_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            officer = ExecutiveOfficer(state_file=os.path.join(d, "missing.json"))
            self.assertEqual(officer.state["devices"]["living_room_light"]["status"], "off")

    def test_corrupt_state_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            state_file = os.path.join(d, "state.json")
            with open(state_file, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            officer = ExecutiveOfficer(state_file=state_file)
            self.assertEqual(officer.state["devices"]["living_room_light"]["status"], "off")


if __name__ == "__main__":
    unittest.main()
