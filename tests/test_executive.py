import os
import tempfile
import time
import unittest

from keerthi.config import CONFIG
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

    def test_set_temp_clamped_to_min(self):
        self.officer.parse_and_execute("[ACTION:SET_TEMP:5]")
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 16)

    def test_set_temp_clamped_to_max(self):
        self.officer.parse_and_execute("[ACTION:SET_TEMP:99]")
        self.assertEqual(self.officer.state["devices"]["bedroom_ac"]["temp"], 30)

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

    def test_tv_on_off(self):
        self.officer.parse_and_execute("[ACTION:TV_ON]")
        self.assertEqual(self.officer.state["devices"]["living_room_tv"]["status"], "on")
        self.officer.parse_and_execute("[ACTION:TV_OFF]")
        self.assertEqual(self.officer.state["devices"]["living_room_tv"]["status"], "off")

    def test_curtain_open_close(self):
        self.officer.parse_and_execute("[ACTION:CURTAIN_OPEN]")
        self.assertEqual(self.officer.state["devices"]["bedroom_curtains"]["status"], "open")
        self.officer.parse_and_execute("[ACTION:CURTAIN_CLOSE]")
        self.assertEqual(self.officer.state["devices"]["bedroom_curtains"]["status"], "closed")

    def test_heater_on_off(self):
        self.officer.parse_and_execute("[ACTION:HEATER_ON]")
        self.assertEqual(self.officer.state["devices"]["bathroom_heater"]["status"], "on")
        self.officer.parse_and_execute("[ACTION:HEATER_OFF]")
        self.assertEqual(self.officer.state["devices"]["bathroom_heater"]["status"], "off")

    def test_heater_temp(self):
        executed = self.officer.parse_and_execute("[ACTION:HEATER_TEMP:45]")
        self.assertIn("Bathroom heater temperature set to 45°C", executed)
        heater = self.officer.state["devices"]["bathroom_heater"]
        self.assertEqual(heater["temp"], 45)
        self.assertEqual(heater["status"], "on")

    def test_heater_temp_clamped_to_50(self):
        self.officer.parse_and_execute("[ACTION:HEATER_TEMP:99]")
        self.assertEqual(self.officer.state["devices"]["bathroom_heater"]["temp"], 50)

    def test_heater_temp_zero_turns_heater_off(self):
        self.officer.parse_and_execute("[ACTION:HEATER_TEMP:0]")
        heater = self.officer.state["devices"]["bathroom_heater"]
        self.assertEqual(heater["temp"], 0)
        self.assertEqual(heater["status"], "off")

    def test_reset_state_restores_defaults(self):
        self.officer.parse_and_execute("[ACTION:LIGHT_ON]")
        self.officer.parse_and_execute("[ACTION:ADD_TASK:Buy milk]")
        executed = self.officer.parse_and_execute("[ACTION:RESET_STATE]")
        self.assertIn("Smart home state reset to defaults.", executed)
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "off")
        self.assertNotIn("Buy milk", self.officer.state["tasks"])

    def test_set_timer_seconds(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TIMER:90]")
        self.assertIn("Timer set for 1m 30s. (Timer 1)", executed)
        timers = self.officer.state["timers"]
        self.assertEqual(len(timers), 1)
        self.assertAlmostEqual(timers[0]["due"], time.time() + 90, delta=2)

    def test_set_timer_minutes_parses_unit(self):
        self.officer.parse_and_execute("[ACTION:SET_TIMER:3:minutes]")
        timer = self.officer.state["timers"][0]
        self.assertAlmostEqual(timer["due"], time.time() + 180, delta=2)

    def test_set_timer_missing_arg_reports(self):
        executed = self.officer.parse_and_execute("[ACTION:SET_TIMER]")
        self.assertIn("specify how long", executed[0])

    def test_fire_due_timers_notifies_and_removes(self):
        self.officer.state["timers"] = [
            {"label": "Timer 1", "due": time.time() - 5},
            {"label": "Timer 2", "due": time.time() + 999},
        ]
        messages = self.officer._fire_due_timers()
        self.assertIn("Timer 'Timer 1' is up!", messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual([t["label"] for t in self.officer.state["timers"]], ["Timer 2"])

    def test_check_timers_reports_pending(self):
        self.officer.state["timers"] = [{"label": "Timer 1", "due": time.time() + 60}]
        executed = self.officer.parse_and_execute("[ACTION:CHECK_TIMERS]")
        self.assertIn("Pending timers: Timer 1", executed[0])

    def test_check_timers_when_none(self):
        executed = self.officer.parse_and_execute("[ACTION:CHECK_TIMERS]")
        self.assertIn("No timers are currently set", executed[0])

    def test_cancel_timer_by_index(self):
        self.officer.state["timers"] = [{"label": "Timer 1", "due": time.time() + 60}]
        executed = self.officer.parse_and_execute("[ACTION:CANCEL_TIMER:0]")
        self.assertIn("Timer cancelled: Timer 1", executed)
        self.assertEqual(self.officer.state["timers"], [])

    def test_cancel_timer_missing_reports(self):
        executed = self.officer.parse_and_execute("[ACTION:CANCEL_TIMER:9]")
        self.assertIn("No timer at index 9", executed[0])

    def test_set_notifier_starts_and_stop_halts(self):
        calls = []
        self.officer.set_notifier(calls.append)
        self.assertTrue(self.officer._running)
        self.officer.stop()
        self.assertFalse(self.officer._running)

    def test_stale_timers_pruned_on_load(self):
        import json

        path = os.path.join(self.tmp.name, "stale.json")
        state = {
            "devices": {},
            "tasks": [],
            "timers": [
                {"label": "Old", "due": time.time() - 3600},
                {"label": "New", "due": time.time() + 3600},
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
        officer = ExecutiveOfficer(state_file=path)
        self.assertEqual([t["label"] for t in officer.state["timers"]], ["New"])

    def test_timer_within_grace_kept_on_load(self):
        import json

        path = os.path.join(self.tmp.name, "grace.json")
        state = {
            "devices": {},
            "tasks": [],
            "timers": [{"label": "Recent", "due": time.time() - 30}],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
        officer = ExecutiveOfficer(state_file=path)
        self.assertEqual([t["label"] for t in officer.state["timers"]], ["Recent"])

    def test_lock_door(self):
        executed = self.officer.parse_and_execute("[ACTION:LOCK_DOOR]")
        self.assertIn("Main entrance: SECURED", executed)
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "locked")

    def test_unlock_door(self):
        self.officer.parse_and_execute("[ACTION:UNLOCK_DOOR]")
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "unlocked")

    def test_safety_intent_skipped_when_confirm_declines(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:UNLOCK_DOOR]", confirm=lambda _: False
        )
        self.assertEqual(executed, [])
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "locked")

    def test_safety_intent_executes_when_confirm_accepts(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:UNLOCK_DOOR]", confirm=lambda _: True
        )
        self.assertIn("Main entrance: UNLOCKED", executed)
        self.assertEqual(self.officer.state["devices"]["main_door"]["status"], "unlocked")

    def test_remove_task_skipped_when_confirm_declines(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:REMOVE_TASK:Call the dentist]", confirm=lambda _: False
        )
        self.assertEqual(executed, [])
        self.assertIn("Call the dentist", self.officer.state["tasks"])

    def test_non_safety_intent_not_gated_by_confirm(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:LIGHT_ON]", confirm=lambda _: False
        )
        self.assertIn("Living room light: ACTIVE", executed)
        self.assertEqual(self.officer.state["devices"]["living_room_light"]["status"], "on")

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

    def test_weather_report_uses_injected_provider(self):
        self.officer.set_weather_provider(lambda loc: "It is sunny here.")
        executed = self.officer.parse_and_execute("[ACTION:WEATHER_REPORT]")
        self.assertEqual(executed, ["It is sunny here."])

    def test_weather_report_passes_user_location(self):
        seen = []
        self.officer.set_weather_provider(lambda loc: seen.append(loc) or "Sunny.")
        self.officer.parse_and_execute("[ACTION:WEATHER_REPORT]")
        self.assertEqual(seen, [CONFIG["LOCATION"]])

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
