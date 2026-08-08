import os
import tempfile
import unittest

from keerthi.executive import ExecutiveOfficer


class TestExecutiveOfficer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.officer = self._make_officer("state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _make_officer(self, name="state.json"):
        return ExecutiveOfficer(state_file=os.path.join(self.tmp.name, name))

    def test_light_on(self):
        executed = self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.assertIn("Living room light: ACTIVE", executed)
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "on")

    def test_light_off(self):
        self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.officer.parse_and_execute("[ACTION:LIGHT_OFF]")
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "off")

    def test_set_brightness(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_BRIGHTNESS:70]")
        self.assertIn("Light brightness set to 70%", executed)
        light = self.officer.state["devices"]["living_room_light"]
        self.assertEqual(light["brightness"], 70)
        self.assertEqual(light["status"], "on")

    def test_set_brightness_clamped_to_100(self):
        self.officer.parse_and_execute("[ACTION:SET_BRIGHTNESS:150]")
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["brightness"], 100)

    def test_set_brightness_zero_turns_light_off(self):
        self.officer.parse_and_execute("[ACTION:SET_BRIGHTNESS:0]")
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "off")

    def test_ac_on_off(self):
        self.officer.parse_and_execute("[ACTION:AC_ON]")
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["status"], "on")
        self.officer.parse_and_execute("[ACTION:AC_OFF]")
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["status"], "off")

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

    def test_fan_on_off(self):
        self.officer.parse_and_execute("[ACTION:FAN_ON]")
        self.assertEqual(self.officer.state["devices"]["kitchen_fan"]["status"], "on")
        self.officer.parse_and_execute("[ACTION:FAN_OFF]")
        self.assertEqual(self.officer.state["devices"]["kitchen_fan"]["status"], "off")

    def test_fan_speed(self):
        executed = self.officer.parse_and_execute("[ACTION:FAN_SPEED:3]")
        self.assertIn("Kitchen fan speed set to 3", executed)
        fan = self.officer.state["devices"]["kitchen_fan"]
        self.assertEqual(fan["speed"], 3)
        self.assertEqual(fan["status"], "on")

    def test_fan_speed_clamped_to_5(self):
        self.officer.parse_and_execute("[ACTION:FAN_SPEED:9]")
        self.assertEqual(self.officer.state["devices"]["kitchen_fan"]["speed"], 5)

    def test_fan_speed_zero_turns_fan_off(self):
        self.officer.parse_and_execute("[ACTION:FAN_SPEED:0]")
        self.assertEqual(self.officer.state["devices"]["kitchen_fan"]["status"], "off")

    def test_fan_speed_non_numeric_is_ignored(self):
        executed = self.officer.parse_and_execute("[ACTION:FAN_SPEED:fast]")
        self.assertEqual(executed, [])

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

    def test_remove_task(self):
        executed = self.officer.parse_and_execute("[ACTION:REMOVE_TASK:Call the dentist]")
        self.assertIn("Task removed: Call the dentist", executed)
        self.assertNotIn("Call the dentist", self.officer.state["tasks"])

    def test_remove_task_missing_returns_message(self):
        executed = self.officer.parse_and_execute("[ACTION:REMOVE_TASK:Nonexistent task]")
        self.assertIn("No task found named 'Nonexistent task'.", executed)

    def test_status_report_mentions_devices_and_tasks(self):
        report = self.officer.parse_and_execute("[ACTION:STATUS_REPORT]")
        self.assertTrue(report)
        self.assertIn("living_room_light", report[0])
        self.assertIn("Tasks:", report[0])

    def test_unknown_intent_is_ignored(self):
        executed = self.officer.parse_and_execute("[ACTION:DOOM_LAUNCH]")
        self.assertEqual(executed, [])

    def test_multiple_actions_in_one_response(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:LIGHT_ON][ACTION:SET_TEMP:20][ACTION:ADD_TASK:Call dentist]"
        )
        self.assertEqual(len(executed), 3)

    def test_state_not_shared_between_instances(self):
        other = self._make_officer("other.json")
        self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.assertEqual(other.state["devices"]["living_room_light"]["status"], "off")

    def test_get_summary_returns_state(self):
        self.assertIs(self.officer.get_summary(), self.officer.state)


if __name__ == "__main__":
    unittest.main()
