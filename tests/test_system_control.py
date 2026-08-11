import os
import sys
import tempfile
import unittest
from unittest import mock

import keerthi.system as system
from keerthi.config import CONFIG


class FakePyautogui:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def write(self, text: str, interval: float = 0) -> None:
        self.calls.append(("write", text, interval))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", keys))

    def moveTo(self, x: int, y: int, duration: float = 0) -> None:
        self.calls.append(("moveTo", x, y, duration))

    def click(self, *args, **kwargs) -> None:
        self.calls.append(("click", args, kwargs))

    def scroll(self, amount: int) -> None:
        self.calls.append(("scroll", amount))

    def screenshot(self):
        return FakeImage()


class FakeImage:
    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(b"png")


class FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def copy(self, text: str) -> None:
        self.text = text


class FakeVolume:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.level = 0.5
        self.muted = True

    def SetMasterVolumeLevelScalar(self, level: float, _ctx) -> None:
        self.calls.append(("set", level))

    def GetMasterVolumeLevelScalar(self) -> float:
        return self.level

    def SetMute(self, value: int, _ctx) -> None:
        self.calls.append(("mute", value))

    def GetMute(self) -> bool:
        return self.muted


class FakeWin32Gui:
    def __init__(self) -> None:
        self.windows = [
            {"hwnd": 10, "title": "Notepad"},
            {"hwnd": 20, "title": "Chrome - Docs"},
        ]
        self.calls: list[tuple] = []

    def IsWindowVisible(self, _hwnd: int) -> bool:
        return True

    def GetWindowText(self, hwnd: int) -> str:
        for w in self.windows:
            if w["hwnd"] == hwnd:
                return w["title"]
        return ""

    def EnumWindows(self, callback, extra) -> None:
        for w in self.windows:
            callback(w["hwnd"], extra)

    def IsIconic(self, _hwnd: int) -> bool:
        return False

    def SetForegroundWindow(self, hwnd: int) -> None:
        self.calls.append(("foreground", hwnd))

    def ShowWindow(self, hwnd: int, command: int) -> None:
        self.calls.append(("show", hwnd, command))

    def PostMessage(self, hwnd: int, msg: int, *_args) -> None:
        self.calls.append(("post", hwnd, msg))

    def GetWindowRect(self, _hwnd: int) -> tuple[int, int, int, int]:
        return (0, 0, 400, 300)

    def SetWindowPos(
        self, hwnd: int, _after: int, x: int, y: int, w: int, h: int, flags: int
    ) -> None:
        self.calls.append(("setpos", hwnd, x, y, w, h, flags))


class FakeWin32Con:
    SW_RESTORE = 9
    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3


class TestInputAutomation(unittest.TestCase):
    def _patch_pyautogui(self, fake: FakePyautogui | None = None):
        return mock.patch("keerthi.system._load_pyautogui", return_value=fake)

    def test_type_text_success(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.type_text("hello world"), "hello world")
        self.assertEqual(fake.calls[0][0], "write")
        self.assertEqual(fake.calls[0][1], "hello world")

    def test_type_text_clipboard_fallback(self):
        fake = FakePyautogui()
        fake.write = mock.Mock(side_effect=Exception("no keyboard"))
        clipboard = FakeClipboard()
        with self._patch_pyautogui(fake), mock.patch.dict(
            sys.modules, {"pyperclip": clipboard}
        ):
            self.assertEqual(system.type_text("hello"), "hello")
        self.assertEqual(clipboard.text, "hello")
        self.assertEqual(fake.calls[0], ("hotkey", ("ctrl", "v")))

    def test_type_text_unavailable(self):
        with self._patch_pyautogui(None):
            self.assertEqual(system.type_text("hi"), "")

    def test_press_keys_hotkey(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.press_keys("ctrl+c"), "ctrl+c")
        self.assertEqual(fake.calls[0], ("hotkey", ("ctrl", "c")))

    def test_press_keys_empty(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.press_keys("   "), "")
        self.assertEqual(fake.calls, [])

    def test_move_mouse(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.move_mouse(500, 400), "(500, 400)")
        self.assertEqual(fake.calls[0][:4], ("moveTo", 500, 400, 0.2))

    def test_click_mouse_with_coordinates(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(
                system.click_mouse(100, 200, button="right"),
                "right click at (100, 200)",
            )
        self.assertEqual(fake.calls[0][1], (100, 200))

    def test_click_mouse_current_position(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.click_mouse(), "left click")
        self.assertEqual(fake.calls[0][1], (None, None))

    def test_scroll_down(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.scroll_mouse("down", 3), "down 3")
        self.assertEqual(fake.calls[0], ("scroll", -3))

    def test_scroll_up(self):
        fake = FakePyautogui()
        with self._patch_pyautogui(fake):
            self.assertEqual(system.scroll_mouse("up", 2), "up 2")
        self.assertEqual(fake.calls[0], ("scroll", 2))


class TestScreenshots(unittest.TestCase):
    def test_take_screenshot_saves_file(self):
        fake = FakePyautogui()
        with (
            mock.patch("keerthi.system._load_pyautogui", return_value=fake),
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.dict(CONFIG, {"SCREENSHOT_DIR": tmp}),
        ):
            path = system.take_screenshot()
            self.assertTrue(path.startswith(tmp))
            self.assertTrue(path.endswith(".png"))
            self.assertTrue(os.path.exists(path))

    def test_take_screenshot_unavailable(self):
        with mock.patch("keerthi.system._load_pyautogui", return_value=None):
            self.assertEqual(system.take_screenshot(), "")

    def test_latest_screenshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(tmp, exist_ok=True)
            newest = os.path.join(tmp, "screenshot-20260101-000002.png")
            older = os.path.join(tmp, "screenshot-20260101-000001.png")
            with open(older, "wb") as f:
                f.write(b"a")
            with open(newest, "wb") as f:
                f.write(b"b")
            with mock.patch.dict(CONFIG, {"SCREENSHOT_DIR": tmp}):
                self.assertEqual(system.latest_screenshot(), newest)

    def test_latest_screenshot_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            CONFIG, {"SCREENSHOT_DIR": tmp}
        ):
            self.assertEqual(system.latest_screenshot(), "")


class TestPowerAndDisplay(unittest.TestCase):
    def _patch_run(self):
        return mock.patch("keerthi.system.subprocess.run")

    def test_shutdown_system(self):
        with self._patch_run() as run:
            self.assertEqual(system.shutdown_system(), "Shutdown scheduled.")
        self.assertEqual(run.call_args.args[0], ["shutdown", "/s", "/t", "5"])

    def test_restart_system(self):
        with self._patch_run() as run:
            self.assertEqual(system.restart_system(), "Restart scheduled.")
        self.assertEqual(run.call_args.args[0], ["shutdown", "/r", "/t", "5"])

    def test_sleep_system(self):
        with self._patch_run() as run:
            self.assertEqual(system.sleep_system(), "Sleeping.")
        self.assertEqual(
            run.call_args.args[0],
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        )

    def test_lock_screen(self):
        with self._patch_run() as run:
            self.assertEqual(system.lock_screen(), "Locking the screen.")
        self.assertEqual(
            run.call_args.args[0],
            ["rundll32.exe", "user32.dll,LockWorkStation"],
        )

    def test_power_unsupported_off_windows(self):
        with mock.patch("keerthi.system.os.name", "posix"):
            self.assertIn(
                "only supported on Windows", system.shutdown_system()
            )

    def test_set_volume(self):
        volume = FakeVolume()
        with mock.patch(
            "keerthi.system._load_volume_interface", return_value=volume
        ):
            self.assertEqual(system.set_volume(50), "50%")
        self.assertEqual(volume.calls[0], ("set", 0.5))

    def test_set_volume_clamps(self):
        volume = FakeVolume()
        with mock.patch(
            "keerthi.system._load_volume_interface", return_value=volume
        ):
            system.set_volume(150)
        self.assertEqual(volume.calls[0][1], 1.0)

    def test_set_volume_unavailable(self):
        with mock.patch(
            "keerthi.system._load_volume_interface", return_value=None
        ):
            self.assertEqual(system.set_volume(50), "")

    def test_set_mute(self):
        volume = FakeVolume()
        with mock.patch(
            "keerthi.system._load_volume_interface", return_value=volume
        ):
            self.assertEqual(system.set_mute(True), "muted")
        self.assertEqual(volume.calls[0], ("mute", 1))

    def test_get_volume_state(self):
        volume = FakeVolume()
        with mock.patch(
            "keerthi.system._load_volume_interface", return_value=volume
        ):
            self.assertEqual(
                system.get_volume_state(), {"percent": 50, "muted": True}
            )

    def test_set_brightness(self):
        completed = mock.MagicMock(returncode=0)
        with mock.patch(
            "keerthi.system.subprocess.run", return_value=completed
        ) as run:
            self.assertEqual(system.set_brightness(70), "70%")
        script = run.call_args.args[0][-1]
        self.assertIn("WmiSetBrightness(1,70)", script)

    def test_set_brightness_requires_elevation(self):
        completed = mock.MagicMock(returncode=1)
        with mock.patch(
            "keerthi.system.subprocess.run", return_value=completed
        ):
            result = system.set_brightness(70)
        self.assertIn("administrator", result)

    def test_set_brightness_off_windows(self):
        with mock.patch("keerthi.system.os.name", "posix"):
            self.assertIn(
                "only supported on Windows", system.set_brightness(70)
            )


class TestWindowManagement(unittest.TestCase):
    def _patch_win32(self, gui: FakeWin32Gui | None = None):
        gui = gui or FakeWin32Gui()
        return mock.patch(
            "keerthi.system._load_win32", return_value=(gui, FakeWin32Con())
        ), gui

    def test_list_windows(self):
        with self._patch_win32()[0]:
            rows = system.list_windows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"hwnd": 10, "title": "Notepad"})

    def test_list_windows_unavailable(self):
        with mock.patch("keerthi.system._load_win32", return_value=(None, None)):
            self.assertEqual(system.list_windows(), [])

    def test_focus_window(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.focus_window("notepad")
        self.assertIn("Focused", result)
        self.assertEqual(gui.calls[0], ("foreground", 10))

    def test_focus_window_not_found(self):
        with self._patch_win32()[0]:
            result = system.focus_window("safari")
        self.assertIn("No open window", result)

    def test_minimize_window(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.minimize_window("notepad")
        self.assertIn("Minimized", result)
        self.assertEqual(gui.calls[0], ("show", 10, FakeWin32Con.SW_MINIMIZE))

    def test_maximize_window(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.maximize_window("notepad")
        self.assertIn("Maximized", result)
        self.assertEqual(gui.calls[0], ("show", 10, FakeWin32Con.SW_MAXIMIZE))

    def test_close_window(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.close_window("notepad")
        self.assertIn("Closing", result)
        self.assertEqual(gui.calls[0], ("post", 10, 0x0010))

    def test_move_window_with_size(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.move_window("notepad", 100, 100, 800, 600)
        self.assertIn("Moved", result)
        self.assertEqual(gui.calls[0], ("setpos", 10, 100, 100, 800, 600, 0x0040))

    def test_move_window_keeps_current_size(self):
        patch, gui = self._patch_win32()
        with patch:
            result = system.move_window("notepad", 5, 6)
        self.assertIn("Moved", result)
        self.assertEqual(gui.calls[0], ("setpos", 10, 5, 6, 400, 300, 0x0040))

    def test_move_window_not_found(self):
        with self._patch_win32()[0]:
            result = system.move_window("safari", 0, 0)
        self.assertIn("No open window", result)

    def test_move_window_to_monitor(self):
        monitors = [
            {"index": 0, "left": 0, "top": 0, "width": 1920, "height": 1080, "primary": True},
            {"index": 1, "left": 1920, "top": 0, "width": 1280, "height": 1024, "primary": False},
        ]
        patch, gui = self._patch_win32()
        with patch, mock.patch("keerthi.system.list_monitors", return_value=monitors):
            result = system.move_window_to_monitor("notepad", 1)
        self.assertIn("monitor 1", result)
        self.assertEqual(
            gui.calls[0],
            ("setpos", 10, 1920 + (1280 - 400) // 2, (1024 - 300) // 2, 400, 300, 0x0040),
        )

    def test_move_window_to_monitor_bad_index(self):
        monitors = [
            {
                "index": 0,
                "left": 0,
                "top": 0,
                "width": 1920,
                "height": 1080,
                "primary": True,
            }
        ]
        with self._patch_win32()[0], mock.patch(
            "keerthi.system.list_monitors", return_value=monitors
        ):
            result = system.move_window_to_monitor("notepad", 3)
        self.assertIn("No monitor at index 3", result)

    def test_list_monitors_non_windows(self):
        with mock.patch("keerthi.system.os.name", "posix"):
            self.assertEqual(system.list_monitors(), [])


class TestInstallApp(unittest.TestCase):
    def test_install_app_success(self):
        completed = mock.MagicMock(returncode=0, stdout="Successfully installed", stderr="")
        with mock.patch("keerthi.system.os.name", "nt"), mock.patch(
            "keerthi.system.subprocess.run", return_value=completed
        ) as run:
            result = system.install_app("7zip")
        self.assertIn("Installed 7zip", result)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "winget")
        self.assertIn("--accept-package-agreements", command)

    def test_install_app_failure(self):
        completed = mock.MagicMock(returncode=1, stdout="", stderr="No package found")
        with mock.patch("keerthi.system.os.name", "nt"), mock.patch(
            "keerthi.system.subprocess.run", return_value=completed
        ):
            result = system.install_app("nope")
        self.assertIn("Could not install 'nope'", result)

    def test_install_app_non_windows(self):
        with mock.patch("keerthi.system.os.name", "posix"):
            self.assertEqual(
                system.install_app("7zip"),
                "Installing apps is only supported on Windows.",
            )

    def test_install_app_winget_missing(self):
        with mock.patch("keerthi.system.os.name", "nt"), mock.patch(
            "keerthi.system.subprocess.run", side_effect=FileNotFoundError
        ):
            result = system.install_app("7zip")
        self.assertIn("winget is not available", result)

    def test_install_app_empty(self):
        self.assertEqual(system.install_app("  "), "No app name given to install.")


class TestBrowser(unittest.TestCase):
    def test_open_url_adds_scheme(self):
        with mock.patch("keerthi.system.webbrowser.open", return_value=True) as op:
            result = system.open_url("example.com")
        self.assertEqual(result, "Opened https://example.com.")
        op.assert_called_once_with("https://example.com")

    def test_open_url_keeps_scheme(self):
        with mock.patch("keerthi.system.webbrowser.open", return_value=True) as op:
            system.open_url("https://example.com/a")
        op.assert_called_once_with("https://example.com/a")

    def test_open_url_empty(self):
        self.assertEqual(system.open_url("  "), "No URL given to open.")

    def test_web_search_encodes_query(self):
        with mock.patch("keerthi.system.webbrowser.open", return_value=True) as op:
            result = system.web_search("best AI models")
        self.assertIn("Opened", result)
        url = op.call_args.args[0]
        self.assertIn("google.com/search?q=", url)
        self.assertIn("best%20AI%20models", url)

    def test_known_apps_extended(self):
        apps = system.known_apps()
        for app in ("chrome", "edge", "settings", "word", "excel"):
            self.assertIn(app, apps)


if __name__ == "__main__":
    unittest.main()
