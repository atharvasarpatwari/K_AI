import logging
import unittest
from unittest import mock

from keerthi.brain import KeerthiBrain
from keerthi.config import CONFIG


class TestKeerthiBrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logging.getLogger("keerthi.brain").setLevel(logging.CRITICAL)

    def _make_brain(self, reply_text: str = "Hello!"):
        brain = object.__new__(KeerthiBrain)
        brain.config = {}
        brain.history = []
        brain.client = mock.MagicMock()
        brain.client.models.generate_content.return_value.text = reply_text
        return brain

    def _make_real_brain(self, reply_text: str = "Hello!"):
        with mock.patch.dict(CONFIG, {"GEMINI_API_KEY": "test-key"}):
            brain = KeerthiBrain()
        brain.client = mock.MagicMock()
        brain.client.models.generate_content.return_value.text = reply_text
        return brain

    def test_init_requires_api_key(self):
        with mock.patch.dict(CONFIG, {"GEMINI_API_KEY": ""}), self.assertRaises(ValueError):
            KeerthiBrain()

    def test_generate_response_returns_text_and_updates_history(self):
        brain = self._make_real_brain(reply_text="Sure thing.")
        result = brain.generate_response("turn on the light")
        self.assertEqual(result, "Sure thing.")
        self.assertEqual(len(brain.history), 2)
        self.assertEqual(brain.history[0]["role"], "user")
        self.assertEqual(brain.history[1]["role"], "model")
        self.assertEqual(brain.history[1]["parts"][0]["text"], "Sure thing.")

    def test_generate_response_passes_history_and_config(self):
        brain = self._make_real_brain(reply_text="OK")
        brain.generate_response("hello")
        call_kwargs = brain.client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], CONFIG["MODEL_NAME"])
        self.assertEqual(call_kwargs["config"], brain.config)
        self.assertEqual(call_kwargs["contents"][0]["parts"][0]["text"], "hello")

    def test_generate_response_handles_none_text(self):
        brain = self._make_brain()
        brain.client.models.generate_content.return_value.text = None
        result = brain.generate_response("hi")
        self.assertEqual(result, "")

    def test_generate_response_swallows_api_exception(self):
        brain = self._make_brain()
        brain.client.models.generate_content.side_effect = RuntimeError("boom")
        result = brain.generate_response("hi")
        self.assertEqual(result, "I hit a technical snag. Please try that again.")
        self.assertEqual(len(brain.history), 1)
        self.assertEqual(brain.history[0]["role"], "user")

    def test_generate_response_never_leaks_raw_error(self):
        brain = self._make_brain()
        brain.client.models.generate_content.side_effect = RuntimeError("SECRET-INTERNAL")
        result = brain.generate_response("hi")
        self.assertNotIn("SECRET-INTERNAL", result)

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

    def test_describe_image_passes_image_to_gemini(self):
        import os
        import tempfile
        from pathlib import Path

        brain = self._make_brain(reply_text="A browser window is open.")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shot.png")
            Path(path).write_bytes(b"fake-png-bytes")
            result = brain.describe_image(path)

        self.assertEqual(result, "A browser window is open.")
        call_kwargs = brain.client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], CONFIG["MODEL_NAME"])
        contents = call_kwargs["contents"]
        parts = contents[0].parts
        self.assertEqual(len(parts), 2)
        self.assertIn("Describe", parts[0].text)
        self.assertEqual(parts[1].inline_data.mime_type, "image/png")
        self.assertEqual(parts[1].inline_data.data, b"fake-png-bytes")

    def test_describe_image_missing_file(self):
        brain = self._make_brain(reply_text="should not matter")
        self.assertEqual(brain.describe_image("C:/does/not/exist.png"), "")

    def test_describe_image_swallows_api_exception(self):
        import os
        import tempfile
        from pathlib import Path

        brain = self._make_brain(reply_text="irrelevant")
        brain.client.models.generate_content.side_effect = RuntimeError("boom")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shot.png")
            Path(path).write_bytes(b"png")
            result = brain.describe_image(path)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
