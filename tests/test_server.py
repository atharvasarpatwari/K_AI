import unittest
from unittest import mock

from fastapi.testclient import TestClient

import keerthi.server as server


class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        self.brain = mock.MagicMock()
        self.officer = mock.MagicMock()
        self.officer.get_summary.return_value = {
            "system": {
                "cpu": 10,
                "cores": 8,
                "memoryUsed": 1 << 30,
                "memoryTotal": 8 << 30,
                "memoryPercent": 12,
                "diskUsed": 1 << 30,
                "diskTotal": 8 << 30,
                "diskPercent": 12,
                "batteryPercent": 90,
                "batteryCharging": True,
                "uptime": 60,
                "platform": "Windows",
                "hostname": "test",
                "python": "3.13",
            },
            "processes": [],
            "tasks": [],
            "timers": [],
        }
        self.officer.parse_and_execute.return_value = ["Opened notepad."]
        server._brain = self.brain
        server._officer = self.officer
        server._pending_confirmations.clear()
        server._clients.clear()
        self.client = TestClient(server.app)

    def tearDown(self):
        server._brain = None
        server._officer = None
        server._controller = None
        server._pending_confirmations.clear()
        server._clients.clear()

    def test_get_state(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.officer.get_summary())

    def test_reset_conversation(self):
        response = self.client.post("/api/reset")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.brain.reset_conversation.assert_called_once()

    def test_chat_normal_flow(self):
        self.brain.generate_response.return_value = "Done. [ACTION:OPEN_APP:notepad]"
        response = self.client.post("/api/chat", json={"message": "open notepad"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reply"], "Done. [ACTION:OPEN_APP:notepad]")
        self.assertEqual(payload["actions"], ["Opened notepad."])
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["state"], self.officer.get_summary())
        self.officer.parse_and_execute.assert_called_once()

    def test_chat_safety_action_requires_confirmation(self):
        self.brain.generate_response.return_value = "Killing process. [ACTION:KILL_PROCESS:1234]"
        response = self.client.post("/api/chat", json={"message": "kill the process"})
        payload = response.json()
        self.assertTrue(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], [])
        self.assertEqual(payload["pendingIntents"], ["KILL_PROCESS"])
        self.assertIsNotNone(payload["confirmationToken"])
        self.officer.parse_and_execute.assert_not_called()
        self.brain.generate_response.assert_called_once()

    def test_confirm_executes_without_regenerating(self):
        self.brain.generate_response.return_value = "Killing process. [ACTION:KILL_PROCESS:1234]"
        first = self.client.post("/api/chat", json={"message": "kill the process"}).json()
        token = first["confirmationToken"]
        response = self.client.post("/api/confirm", json={"token": token})
        payload = response.json()
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], ["Opened notepad."])
        self.officer.parse_and_execute.assert_called_once()
        self.brain.generate_response.assert_called_once()

    def test_confirm_token_is_single_use(self):
        self.brain.generate_response.return_value = "Killing process. [ACTION:KILL_PROCESS:1234]"
        token = self.client.post(
            "/api/chat", json={"message": "kill the process"}
        ).json()["confirmationToken"]
        self.client.post("/api/confirm", json={"token": token})
        second = self.client.post("/api/confirm", json={"token": token})
        self.assertEqual(second.status_code, 404)

    def test_confirm_cancel_runs_nothing(self):
        self.brain.generate_response.return_value = "Killing process. [ACTION:KILL_PROCESS:1234]"
        token = self.client.post(
            "/api/chat", json={"message": "kill the process"}
        ).json()["confirmationToken"]
        response = self.client.post(
            "/api/confirm", json={"token": token, "confirmed": False}
        )
        payload = response.json()
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], [])
        self.officer.parse_and_execute.assert_not_called()

    def test_chat_safety_action_runs_when_confirmed(self):
        self.brain.generate_response.return_value = "Killing process. [ACTION:KILL_PROCESS:1234]"
        response = self.client.post(
            "/api/chat", json={"message": "kill the process", "confirmed": True}
        )
        payload = response.json()
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], ["Opened notepad."])
        self.officer.parse_and_execute.assert_called_once()

    def test_chat_missing_message_is_422(self):
        response = self.client.post("/api/chat", json={})
        self.assertEqual(response.status_code, 422)

    def test_action_executes_intent_directly(self):
        self.officer.parse_and_execute.return_value = ["Opened notepad."]
        response = self.client.post(
            "/api/action", json={"intent": "OPEN_APP", "args": ["notepad"]}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], ["Opened notepad."])
        self.officer.parse_and_execute.assert_called_once_with("[ACTION:OPEN_APP:notepad]")

    def test_action_safety_requires_confirmation(self):
        response = self.client.post(
            "/api/action", json={"intent": "KILL_PROCESS", "args": ["1234"]}
        )
        payload = response.json()
        self.assertTrue(payload["needsConfirmation"])
        self.assertEqual(payload["pendingIntents"], ["KILL_PROCESS"])
        self.assertIsNotNone(payload["confirmationToken"])
        self.officer.parse_and_execute.assert_not_called()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["version"], "2.3.0")
        self.assertIn("apiKeyPresent", payload)

    def test_transcribe_audio(self):
        controller = mock.MagicMock()
        controller._transcribe.return_value = "turn on the light"
        server._controller = controller
        response = self.client.post("/api/transcribe", content=b"\x00" * 3200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": "turn on the light"})
        controller._transcribe.assert_called_once()

    def test_transcribe_audio_failure(self):
        controller = mock.MagicMock()
        controller._transcribe.return_value = ""
        server._controller = controller
        response = self.client.post("/api/transcribe", content=b"\x00" * 3200)
        self.assertEqual(response.status_code, 422)

    def test_transcribe_empty_body(self):
        controller = mock.MagicMock()
        server._controller = controller
        response = self.client.post("/api/transcribe", content=b"")
        self.assertEqual(response.status_code, 400)
        controller._transcribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
