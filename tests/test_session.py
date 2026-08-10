import unittest
from unittest import mock

from main import ConversationSession


class TestConversationSession(unittest.TestCase):
    def setUp(self):
        self.brain = mock.Mock()
        self.officer = mock.Mock()
        self.peripherals = mock.Mock()
        self.session = ConversationSession(
            brain=self.brain,
            officer=self.officer,
            peripherals=self.peripherals,
        )

    def test_exit_phrase_ends_session(self):
        result = self.session.handle_input("exit")
        self.assertEqual(result, "exit")
        self.peripherals.speak.assert_called_once()

    def test_empty_input_is_skipped(self):
        result = self.session.handle_input("   ")
        self.assertIsNone(result)
        self.brain.generate_response.assert_not_called()
        self.peripherals.speak.assert_not_called()

    def test_wake_word_is_acknowledged(self):
        result = self.session.handle_input("Keerthi")
        self.assertIsNone(result)
        self.brain.generate_response.assert_not_called()
        self.peripherals.speak.assert_called_once()

    def test_reset_clears_conversation(self):
        result = self.session.handle_input("/reset")
        self.assertIsNone(result)
        self.brain.reset_conversation.assert_called_once()
        self.brain.generate_response.assert_not_called()

    def test_normal_flow_responds(self):
        self.brain.generate_response.return_value = "Here you go."
        self.officer.parse_and_execute.return_value = []
        result = self.session.handle_input("add a task")
        self.assertIsNone(result)
        self.brain.generate_response.assert_called_once_with("add a task")
        self.peripherals.speak.assert_any_call("Here you go.")

    def test_normal_flow_shows_dashboard_when_actions_executed(self):
        self.brain.generate_response.return_value = "Done."
        self.officer.parse_and_execute.return_value = ["Light is on"]
        self.session.handle_input("turn on the light")
        self.peripherals.speak.assert_any_call("Light is on")
        self.peripherals.show_dashboard.assert_called_once()

    def test_run_loop_exits_and_closes_peripherals(self):
        self.peripherals.listen.side_effect = ["hello", "exit"]
        self.brain.generate_response.return_value = "hi"
        self.officer.parse_and_execute.return_value = []
        self.session.run()
        self.peripherals.close.assert_called_once()
        self.assertEqual(self.peripherals.listen.call_count, 2)

    def test_confirm_action_accepts_yes(self):
        self.peripherals.listen.return_value = "yes"
        self.assertTrue(self.session._confirm_action("UNLOCK_DOOR"))

    def test_confirm_action_accepts_yeah(self):
        self.peripherals.listen.return_value = "yeah"
        self.assertTrue(self.session._confirm_action("UNLOCK_DOOR"))

    def test_confirm_action_rejects_no(self):
        self.peripherals.listen.return_value = "no"
        self.assertFalse(self.session._confirm_action("UNLOCK_DOOR"))

    def test_handle_input_passes_confirm_callback(self):
        self.brain.generate_response.return_value = "Unlocking. [ACTION:UNLOCK_DOOR]"
        self.officer.parse_and_execute.return_value = []
        self.session.handle_input("unlock the door")
        self.officer.parse_and_execute.assert_called_once()
        call_kwargs = self.officer.parse_and_execute.call_args.kwargs
        self.assertIn("confirm", call_kwargs)


if __name__ == "__main__":
    unittest.main()
