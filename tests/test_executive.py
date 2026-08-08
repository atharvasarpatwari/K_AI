import unittest

from keerthi.executive import ExecutiveOfficer


class TestExecutiveOfficer(unittest.TestCase):
    def setUp(self):
        self.officer = ExecutiveOfficer()

    def test_light_on(self):
        executed = self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.assertIn("Living room light: ACTIVE", executed)
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "on")

    def test_light_off(self):
        self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.officer.parse_and_execute("[ACTION:LIGHT_OFF]")
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "off")

    def test_set_temp_plain_number(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TEMP:24]")
        self.assertIn("Climate adjusted to 24°C", executed)
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 24)

    def test_set_temp_with_words(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TEMP:set to 21 degrees]")
        self.assertIn("Climate adjusted to 21°C", executed)
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 21)

    def test_set_temp_defaults_to_22_without_args(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TEMP]")
        self.assertIn("Climate adjusted to 22°C", executed)
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 22)

    def test_set_temp_non_numeric_arg_is_ignored(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TEMP:degrees]")
        self.assertEqual(executed, [])
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 22)

    def test_lock_door(self):
        executed = self.officer.parse_and_execute("[ACTION:LOCK_DOOR]")
        self.assertIn("Main entrance: SECURED", executed)
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "locked")

    def test_unlock_door(self):
        self.officer.parse_and_execute("[ACTION:UNLOCK_DOOR]")
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "unlocked")

    def test_add_task_strips_whitespace(self):
        executed = self.officer.parse_and_execute("[ACTION:ADD_TASK: Buy milk]")
        self.assertIn("Task synchronization successful: Buy milk", executed)
        self.assertIn("Buy milk", self.officer.state["tasks"])

    def test_add_task_default_name(self):
        self.officer.parse_and_execute("[ACTION:ADD_TASK]")
        self.assertIn("New Task", self.officer.state["tasks"])

    def test_unknown_intent_is_ignored(self):
        executed = self.officer.parse_and_execute("[ACTION:DOOM_LAUNCH]")
        self.assertEqual(executed, [])

    def test_multiple_actions_in_one_response(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:LIGHT_ON][ACTION:SET_TEMP:20][ACTION:ADD_TASK:Call dentist]"
        )
        self.assertEqual(len(executed), 3)

    def test_state_not_shared_between_instances(self):
        other = ExecutiveOfficer()
        self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.assertEqual(other.state["devices"]["living_room_light"]["status"], "off")

    def test_get_summary_returns_state(self):
        self.assertIs(self.officer.get_summary(), self.officer.state)


if __name__ == "__main__":
    unittest.main()
