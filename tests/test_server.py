import unittest
from unittest import mock

from fastapi.testclient import TestClient

import keerthi.server as server


class TestServerEndpoints(unittest.TestCase):
    def setUp(self):
        self.brain = mock.MagicMock()
        self.officer = mock.MagicMock()
        self.officer.get_summary.return_value = {
            "devices": {},
            "tasks": [],
            "timers": [],
        }
        self.officer.parse_and_execute.return_value = ["Light is on"]
        server._brain = self.brain
        server._officer = self.officer
        self.client = TestClient(server.app)

    def tearDown(self):
        server._brain = None
        server._officer = None

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
        self.brain.generate_response.return_value = "Done. [ACTION:LIGHT_ON]"
        response = self.client.post("/api/chat", json={"message": "lights on"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reply"], "Done. [ACTION:LIGHT_ON]")
        self.assertEqual(payload["actions"], ["Light is on"])
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["state"], self.officer.get_summary())
        self.officer.parse_and_execute.assert_called_once()

    def test_chat_safety_action_requires_confirmation(self):
        self.brain.generate_response.return_value = "Unlocking. [ACTION:UNLOCK_DOOR]"
        response = self.client.post("/api/chat", json={"message": "unlock the door"})
        payload = response.json()
        self.assertTrue(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], [])
        self.officer.parse_and_execute.assert_not_called()

    def test_chat_safety_action_runs_when_confirmed(self):
        self.brain.generate_response.return_value = "Unlocking. [ACTION:UNLOCK_DOOR]"
        response = self.client.post(
            "/api/chat", json={"message": "unlock the door", "confirmed": True}
        )
        payload = response.json()
        self.assertFalse(payload["needsConfirmation"])
        self.assertEqual(payload["actions"], ["Light is on"])
        self.officer.parse_and_execute.assert_called_once()

    def test_chat_missing_message_is_422(self):
        response = self.client.post("/api/chat", json={})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
