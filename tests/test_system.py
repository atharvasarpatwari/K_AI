import os
import tempfile
import unittest
from unittest import mock

import psutil

import keerthi.system as system


class TestGetMetrics(unittest.TestCase):
    def _patch(self):
        return mock.patch.multiple(
            "keerthi.system.psutil",
            cpu_percent=mock.DEFAULT,
            cpu_count=mock.DEFAULT,
            virtual_memory=mock.DEFAULT,
            disk_usage=mock.DEFAULT,
            boot_time=mock.DEFAULT,
            sensors_battery=mock.DEFAULT,
        )

    def test_get_metrics_shape(self):
        with self._patch() as mocks:
            mocks["cpu_percent"].return_value = 42.0
            mocks["cpu_count"].return_value = 8
            mocks["virtual_memory"].return_value = mock.MagicMock(
                used=8 * 1024**3, total=16 * 1024**3, percent=50.0
            )
            mocks["disk_usage"].return_value = mock.MagicMock(
                used=100 * 1024**3, total=200 * 1024**3, percent=50.0
            )
            mocks["boot_time"].return_value = 1000
            mocks["sensors_battery"].return_value = mock.MagicMock(
                percent=80.0, power_plugged=True
            )
            with mock.patch("keerthi.system.time.time", return_value=1300):
                m = system.get_metrics()

        self.assertEqual(m["cpu"], 42)
        self.assertEqual(m["cores"], 8)
        self.assertEqual(m["memoryPercent"], 50)
        self.assertEqual(m["memoryTotal"], 16 * 1024**3)
        self.assertEqual(m["diskPercent"], 50)
        self.assertEqual(m["batteryPercent"], 80)
        self.assertTrue(m["batteryCharging"])
        self.assertEqual(m["uptime"], 300)

    def test_get_metrics_without_battery(self):
        with self._patch() as mocks:
            mocks["cpu_percent"].return_value = 0.0
            mocks["cpu_count"].return_value = 4
            mocks["virtual_memory"].return_value = mock.MagicMock(
                used=1, total=2, percent=1.0
            )
            mocks["disk_usage"].return_value = mock.MagicMock(
                used=1, total=2, percent=1.0
            )
            mocks["boot_time"].return_value = 0
            mocks["sensors_battery"].return_value = None
            m = system.get_metrics()

        self.assertIsNone(m["batteryPercent"])
        self.assertIsNone(m["batteryCharging"])


class _FakeProcess:
    def __init__(self, pid: int, name: str, mem: float, cpu: float) -> None:
        self.pid = pid
        self.info = {"pid": pid, "name": name, "memory_percent": mem}
        self._name = name
        self._cpu = cpu
        self._calls = 0

    def name(self) -> str:
        return self._name

    def cpu_percent(self, interval=None) -> float:
        self._calls += 1
        return self._cpu if self._calls > 1 else 0.0


class TestListProcesses(unittest.TestCase):
    @mock.patch("keerthi.system.time.sleep")
    @mock.patch("keerthi.system.psutil.process_iter")
    def test_sorted_by_cpu_and_limited(self, iter_mock, sleep_mock):
        iter_mock.return_value = [
            _FakeProcess(1, "chrome", 10.0, 50.0),
            _FakeProcess(2, "python", 20.0, 90.0),
            _FakeProcess(3, "idle", 1.0, 5.0),
        ]
        rows = system.list_processes(2)
        self.assertEqual([r["name"] for r in rows], ["python", "chrome"])
        self.assertEqual(rows[0]["cpu"], 90)
        self.assertEqual(rows[0]["pid"], 2)
        sleep_mock.assert_called_once()

    @mock.patch("keerthi.system.time.sleep")
    @mock.patch("keerthi.system.psutil.process_iter")
    def test_skips_denied_processes(self, iter_mock, sleep_mock):
        denied = mock.MagicMock()
        denied.cpu_percent.side_effect = psutil.AccessDenied(1)
        iter_mock.return_value = [denied]
        rows = system.list_processes(5)
        self.assertEqual(rows, [])


class TestKillProcess(unittest.TestCase):
    def test_kill_terminates(self):
        proc = mock.MagicMock()
        proc.name.return_value = "chrome"
        with mock.patch("keerthi.system.psutil.Process", return_value=proc):
            result = system.kill_process(1234)
        self.assertIn("Terminated chrome", result)
        proc.terminate.assert_called_once()

    def test_kill_missing_process(self):
        with mock.patch(
            "keerthi.system.psutil.Process",
            side_effect=psutil.NoSuchProcess(999),
        ):
            result = system.kill_process(999)
        self.assertIn("No process found", result)

    def test_kill_access_denied(self):
        with mock.patch(
            "keerthi.system.psutil.Process",
            side_effect=psutil.AccessDenied(1),
        ):
            result = system.kill_process(1)
        self.assertIn("Access denied", result)


class TestOpenApp(unittest.TestCase):
    @mock.patch("keerthi.system.subprocess.Popen")
    def test_opens_known_app(self, popen_mock):
        result = system.open_app("notepad")
        self.assertIn("Opened notepad", result)
        popen_mock.assert_called_once_with(["notepad.exe"])

    @mock.patch("keerthi.system.subprocess.Popen")
    def test_empty_name(self, popen_mock):
        result = system.open_app("   ")
        self.assertIn("No app name", result)
        popen_mock.assert_not_called()

    def test_known_apps_returns_list(self):
        apps = system.known_apps()
        self.assertIsInstance(apps, list)
        self.assertIn("notepad", apps)


class TestRunCommand(unittest.TestCase):
    @mock.patch("keerthi.system.subprocess.run")
    def test_returns_stdout(self, run_mock):
        run_mock.return_value = mock.MagicMock(
            stdout="hello world\n", stderr="", returncode=0
        )
        self.assertEqual(system.run_command("echo hello"), "hello world")

    @mock.patch("keerthi.system.subprocess.run")
    def test_timeout_message(self, run_mock):
        run_mock.side_effect = __import__("subprocess").TimeoutExpired("cmd", 30)
        result = system.run_command("sleep 999")
        self.assertIn("timed out", result)

    @mock.patch("keerthi.system.subprocess.run")
    def test_empty_command(self, run_mock):
        self.assertIn("No command", system.run_command("  "))
        run_mock.assert_not_called()


class TestFileHelpers(unittest.TestCase):
    def test_list_directory(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "sub"))
            with open(os.path.join(d, "a.txt"), "w", encoding="utf-8") as f:
                f.write("x")
            listing = system.list_directory(d)
        self.assertEqual(len(listing["entries"]), 2)
        by_name = {e["name"]: e["isDir"] for e in listing["entries"]}
        self.assertTrue(by_name["sub"])
        self.assertFalse(by_name["a.txt"])

    def test_list_missing_directory_returns_error(self):
        listing = system.list_directory("Z:\\definitely\\missing")
        self.assertIn("error", listing)

    @mock.patch("keerthi.system.os.startfile")
    def test_open_file(self, startfile_mock):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")
            result = system.open_file(path)
        self.assertIn("Opened", result)
        startfile_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
