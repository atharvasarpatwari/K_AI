import os
import tempfile
import time
import unittest
from unittest import mock

from keerthi.config import CONFIG
from keerthi.executive import ExecutiveOfficer

METRICS = {
    "cpu": 42,
    "cores": 8,
    "memoryUsed": 8 * 1024**3,
    "memoryTotal": 16 * 1024**3,
    "memoryPercent": 50,
    "diskUsed": 100 * 1024**3,
    "diskTotal": 200 * 1024**3,
    "diskPercent": 50,
    "batteryPercent": 80,
    "batteryCharging": True,
    "uptime": 300,
    "platform": "Windows",
    "hostname": "test",
    "python": "3.13",
}

PROCESSES = [
    {"pid": 1234, "name": "chrome", "cpu": 90, "memory": 20.0},
    {"pid": 5678, "name": "python", "cpu": 5, "memory": 1.5},
]


class TestExecutiveOfficer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.officer = self._make_officer("state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _make_officer(self, name="state.json"):
        return ExecutiveOfficer(state_file=os.path.join(self.tmp.name, name))

    # ---- System status ----

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_system_status(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:SYSTEM_STATUS]")
        self.assertIn("CPU 42%", executed[0])
        self.assertIn("memory 50%", executed[0])
        self.assertIn("disk 50%", executed[0])
        self.assertIn("battery at 80% (charging)", executed[0])

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_cpu_usage(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:CPU_USAGE]")
        self.assertIn("CPU usage is 42%", executed[0])

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_memory_usage(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:MEMORY_USAGE]")
        self.assertIn("Memory usage is 50%", executed[0])

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_disk_usage(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:DISK_USAGE]")
        self.assertIn("Disk usage is 50%", executed[0])

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_battery_status(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:BATTERY_STATUS]")
        self.assertIn("battery at 80% (charging)", executed[0])

    @mock.patch(
        "keerthi.system.get_metrics",
        return_value={**METRICS, "batteryPercent": None, "batteryCharging": None},
    )
    def test_battery_status_absent(self, _metrics):
        executed = self.officer.parse_and_execute("[ACTION:BATTERY_STATUS]")
        self.assertIn("no battery detected", executed[0])

    # ---- Processes ----

    @mock.patch("keerthi.system.list_processes", return_value=PROCESSES)
    def test_list_processes(self, _procs):
        executed = self.officer.parse_and_execute("[ACTION:LIST_PROCESSES:2]")
        self.assertIn("PID 1234 chrome", executed[0])
        self.assertIn("PID 5678 python", executed[0])

    @mock.patch("keerthi.system.list_processes", return_value=[])
    def test_list_processes_empty(self, _procs):
        executed = self.officer.parse_and_execute("[ACTION:LIST_PROCESSES]")
        self.assertIn("No running processes", executed[0])

    @mock.patch("keerthi.system.kill_process", return_value="Terminated chrome (PID 1234).")
    def test_kill_process(self, kill_mock):
        executed = self.officer.parse_and_execute("[ACTION:KILL_PROCESS:1234]")
        self.assertEqual(executed, ["Terminated chrome (PID 1234)."])
        kill_mock.assert_called_once_with(1234)

    @mock.patch("keerthi.system.kill_process")
    def test_kill_process_missing_pid(self, kill_mock):
        executed = self.officer.parse_and_execute("[ACTION:KILL_PROCESS]")
        self.assertIn("provide a process PID", executed[0])
        kill_mock.assert_not_called()

    @mock.patch("keerthi.system.kill_process", return_value="Terminated chrome (PID 1234).")
    def test_kill_process_declined_by_confirm(self, kill_mock):
        executed = self.officer.parse_and_execute(
            "[ACTION:KILL_PROCESS:1234]", confirm=lambda _: False
        )
        self.assertEqual(executed, [])
        kill_mock.assert_not_called()

    @mock.patch("keerthi.system.kill_process", return_value="Terminated chrome (PID 1234).")
    def test_kill_process_accepted_by_confirm(self, kill_mock):
        executed = self.officer.parse_and_execute(
            "[ACTION:KILL_PROCESS:1234]", confirm=lambda _: True
        )
        self.assertEqual(executed, ["Terminated chrome (PID 1234)."])
        kill_mock.assert_called_once_with(1234)

    # ---- Apps / commands / files ----

    @mock.patch("keerthi.system.open_app", return_value="Opened notepad.")
    def test_open_app(self, open_mock):
        executed = self.officer.parse_and_execute("[ACTION:OPEN_APP:notepad]")
        self.assertEqual(executed, ["Opened notepad."])
        open_mock.assert_called_once_with("notepad")

    @mock.patch("keerthi.system.run_command", return_value="hello world")
    def test_run_command(self, run_mock):
        executed = self.officer.parse_and_execute("[ACTION:RUN_COMMAND:echo hello]")
        self.assertEqual(executed, ["hello world"])
        run_mock.assert_called_once_with("echo hello")

    @mock.patch("keerthi.system.run_command", return_value="hello world")
    def test_run_command_declined_by_confirm(self, run_mock):
        executed = self.officer.parse_and_execute(
            "[ACTION:RUN_COMMAND:echo hello]", confirm=lambda _: False
        )
        self.assertEqual(executed, [])
        run_mock.assert_not_called()

    @mock.patch("keerthi.system.list_directory")
    def test_file_list(self, list_mock):
        list_mock.return_value = {
            "path": "C:\\Users",
            "entries": [
                {"name": "Documents", "isDir": True},
                {"name": "readme.txt", "isDir": False},
            ],
        }
        executed = self.officer.parse_and_execute("[ACTION:FILE_LIST:C:\\Users]")
        self.assertIn("[DIR] Documents", executed[0])
        self.assertIn("readme.txt", executed[0])

    @mock.patch("keerthi.system.list_directory")
    def test_file_list_error(self, list_mock):
        list_mock.return_value = {"path": "Z:\\missing", "entries": [], "error": "no such dir"}
        executed = self.officer.parse_and_execute("[ACTION:FILE_LIST:Z:\\missing]")
        self.assertIn("Could not list", executed[0])

    @mock.patch("keerthi.system.open_file", return_value="Opened C:\\readme.txt.")
    def test_open_file_path_with_colon(self, open_mock):
        executed = self.officer.parse_and_execute("[ACTION:OPEN_FILE:C:\\readme.txt]")
        self.assertEqual(executed, ["Opened C:\\readme.txt."])
        open_mock.assert_called_once_with("C:\\readme.txt")

    # ---- Tasks ----

    def test_add_task(self):
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

    def test_remove_task_declined_by_confirm(self):
        executed = self.officer.parse_and_execute(
            "[ACTION:REMOVE_TASK:Call the dentist]", confirm=lambda _: False
        )
        self.assertEqual(executed, [])
        self.assertIn("Call the dentist", self.officer.state["tasks"])

    def test_remove_task_missing_returns_message(self):
        executed = self.officer.parse_and_execute("[ACTION:REMOVE_TASK:Nonexistent task]")
        self.assertIn("No task found named 'Nonexistent task'.", executed)

    # ---- Reset ----

    def test_reset_state_restores_defaults(self):
        self.officer.parse_and_execute("[ACTION:ADD_TASK:Buy milk]")
        executed = self.officer.parse_and_execute("[ACTION:RESET_STATE]")
        self.assertIn("Tasks and timers reset to defaults.", executed)
        self.assertNotIn("Buy milk", self.officer.state["tasks"])
        self.assertEqual(self.officer.state["timers"], [])

    # ---- Timers ----

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

    # ---- Persistence ----

    def test_stale_timers_pruned_on_load(self):
        import json

        path = os.path.join(self.tmp.name, "stale.json")
        state = {
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
            "tasks": [],
            "timers": [{"label": "Recent", "due": time.time() - 30}],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
        officer = ExecutiveOfficer(state_file=path)
        self.assertEqual([t["label"] for t in officer.state["timers"]], ["Recent"])

    def test_old_device_state_file_is_ignored(self):
        import json

        path = os.path.join(self.tmp.name, "legacy.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"devices": {"living_room_light": {"status": "on"}}}, f)
        officer = ExecutiveOfficer(state_file=path)
        self.assertNotIn("devices", officer.state)
        self.assertEqual(len(officer.state["tasks"]), 3)

    # ---- Weather ----

    def test_weather_report_uses_injected_provider(self):
        self.officer.set_weather_provider(lambda loc: "It is sunny here.")
        executed = self.officer.parse_and_execute("[ACTION:WEATHER_REPORT]")
        self.assertEqual(executed, ["It is sunny here."])

    def test_weather_report_passes_user_location(self):
        seen = []
        self.officer.set_weather_provider(lambda loc: seen.append(loc) or "Sunny.")
        self.officer.parse_and_execute("[ACTION:WEATHER_REPORT]")
        self.assertEqual(seen, [CONFIG["LOCATION"]])

    # ---- Reporting ----

    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_status_report(self, _metrics):
        report = self.officer.parse_and_execute("[ACTION:STATUS_REPORT]")
        self.assertIn("CPU 42%", report[0])
        self.assertIn("Tasks:", report[0])

    @mock.patch("keerthi.system.list_processes", return_value=PROCESSES)
    @mock.patch("keerthi.system.get_metrics", return_value=METRICS)
    def test_get_summary_includes_live_data(self, _metrics, _procs):
        summary = self.officer.get_summary()
        self.assertEqual(summary["system"], METRICS)
        self.assertEqual(summary["processes"], PROCESSES)
        self.assertIn("tasks", summary)
        self.assertIn("timers", summary)

    # ---- General behaviour ----

    def test_unknown_intent_is_ignored(self):
        executed = self.officer.parse_and_execute("[ACTION:DOOM_LAUNCH]")
        self.assertEqual(executed, [])

    def test_multiple_actions_in_one_response(self):
        with (
            mock.patch("keerthi.system.get_metrics", return_value=METRICS),
            mock.patch("keerthi.system.open_app", return_value="Opened notepad."),
        ):
            executed = self.officer.parse_and_execute(
                "[ACTION:CPU_USAGE][ACTION:OPEN_APP:notepad][ACTION:ADD_TASK:Call dentist]"
            )
        self.assertEqual(len(executed), 3)

    def test_state_not_shared_between_instances(self):
        other = self._make_officer("other.json")
        self.officer.parse_and_execute("[ACTION:ADD_TASK:Private task]")
        self.assertNotIn("Private task", other.state["tasks"])

    def test_non_safety_intent_not_gated_by_confirm(self):
        with mock.patch("keerthi.system.open_app", return_value="Opened notepad."):
            executed = self.officer.parse_and_execute(
                "[ACTION:OPEN_APP:notepad]", confirm=lambda _: False
            )
        self.assertEqual(executed, ["Opened notepad."])


if __name__ == "__main__":
    unittest.main()
