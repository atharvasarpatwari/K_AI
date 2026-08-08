import unittest

from keerthi.brain import KeerthiBrain


class TestKeerthiBrain(unittest.TestCase):
    def _make_brain(self):
        brain = object.__new__(KeerthiBrain)
        brain.config = {}
        brain.history = []
        return brain

    def test_trim_history_caps_length(self):
        brain = self._make_brain()
        for i in range(30):
            brain.history.append({"role": "user", "parts": [{"text": str(i)}]})
        brain._trim_history()
        self.assertEqual(len(brain.history), 20)

    def test_trim_history_keeps_recent_first(self):
        brain = self._make_brain()
        for i in range(30):
            brain.history.append({"role": "user", "parts": [{"text": str(i)}]})
        brain._trim_history()
        self.assertEqual(brain.history[0]["parts"][0]["text"], "10")
        self.assertEqual(brain.history[-1]["parts"][0]["text"], "29")

    def test_trim_history_does_nothing_when_short(self):
        brain = self._make_brain()
        brain.history = [{"role": "user", "parts": [{"text": "hi"}]}]
        brain._trim_history()
        self.assertEqual(len(brain.history), 1)

    def test_reset_conversation_clears_history(self):
        brain = self._make_brain()
        brain.history = [{"role": "user", "parts": [{"text": "hi"}]}]
        brain.reset_conversation()
        self.assertEqual(brain.history, [])


if __name__ == "__main__":
    unittest.main()
