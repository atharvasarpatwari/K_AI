import unittest
from unittest import mock

from keerthi.config import CONFIG
from keerthi.peripherals import PeripheralController


class TestPeripheralTranscribe(unittest.TestCase):
    def _make_controller(self, engine: str = "google"):
        with mock.patch.dict(CONFIG, {"STT_ENGINE": engine, "STT_LANGUAGE": "en-US"}):
            controller = object.__new__(PeripheralController)
            controller.recognizer = mock.MagicMock()
            controller._vosk_model = None
            controller._whisper_model = None
            return controller

    def test_google_engine_uses_recognize_google(self):
        controller = self._make_controller(engine="google")
        controller.recognizer.recognize_google.return_value = "hello there"
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "google"}):
            result = controller._transcribe(mock.MagicMock())
        self.assertEqual(result, "hello there")
        controller.recognizer.recognize_google.assert_called_once()

    def test_google_engine_never_loads_vosk(self):
        controller = self._make_controller(engine="google")
        controller.recognizer.recognize_google.return_value = "hi"
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "google"}), mock.patch.object(
            controller, "_transcribe_vosk"
        ) as vosk_mock:
            controller._transcribe(mock.MagicMock())
            vosk_mock.assert_not_called()

    def test_vosk_engine_falls_back_to_google_on_empty(self):
        controller = self._make_controller(engine="vosk")
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "vosk"}), mock.patch.object(
            controller, "_transcribe_vosk", return_value=""
        ) as vosk_mock:
            controller.recognizer.recognize_google.return_value = "fallback"
            result = controller._transcribe(mock.MagicMock())
        self.assertEqual(result, "fallback")
        vosk_mock.assert_called_once()

    def test_vosk_engine_prefers_vosk_text(self):
        controller = self._make_controller(engine="vosk")
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "vosk"}), mock.patch.object(
            controller, "_transcribe_vosk", return_value="offline text"
        ):
            controller.recognizer.recognize_google.return_value = "should not use"
            result = controller._transcribe(mock.MagicMock())
        self.assertEqual(result, "offline text")
        controller.recognizer.recognize_google.assert_not_called()

    def test_vosk_transcription_parses_result(self):
        controller = self._make_controller(engine="vosk")
        audio = mock.MagicMock()
        audio.get_raw_data.return_value = b"\x00" * 3200
        vosk_mod = mock.MagicMock()
        recognizer = vosk_mod.KaldiRecognizer.return_value
        recognizer.AcceptWaveform.return_value = True
        recognizer.Result.return_value = '{"text": "good morning keerthi"}'
        with mock.patch.dict("sys.modules", {"vosk": vosk_mod}):
            result = controller._transcribe_vosk(audio)
        self.assertEqual(result, "good morning keerthi")
        vosk_mod.Model.assert_called_once_with(CONFIG["VOSK_MODEL_PATH"])

    def test_vosk_transcription_empty_on_error(self):
        controller = self._make_controller(engine="vosk")
        audio = mock.MagicMock()
        audio.get_raw_data.side_effect = OSError("no data")
        result = controller._transcribe_vosk(audio)
        self.assertEqual(result, "")

    def test_whisper_engine_prefers_whisper_text(self):
        controller = self._make_controller(engine="whisper")
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "whisper"}), mock.patch.object(
            controller, "_transcribe_whisper", return_value="offline text"
        ):
            controller.recognizer.recognize_google.return_value = "should not use"
            result = controller._transcribe(mock.MagicMock())
        self.assertEqual(result, "offline text")
        controller.recognizer.recognize_google.assert_not_called()

    def test_whisper_engine_falls_back_to_google_on_empty(self):
        controller = self._make_controller(engine="whisper")
        with mock.patch.dict(CONFIG, {"STT_ENGINE": "whisper"}), mock.patch.object(
            controller, "_transcribe_whisper", return_value=""
        ) as whisper_mock:
            controller.recognizer.recognize_google.return_value = "fallback"
            result = controller._transcribe(mock.MagicMock())
        self.assertEqual(result, "fallback")
        whisper_mock.assert_called_once()

    def test_whisper_transcription_parses_result(self):
        controller = self._make_controller(engine="whisper")
        audio = mock.MagicMock()
        audio.get_raw_data.return_value = b"\x00" * 3200
        whisper_mod = mock.MagicMock()
        model = whisper_mod.WhisperModel.return_value
        seg = mock.MagicMock()
        seg.text = "good morning"
        model.transcribe.return_value = ([seg], {})
        with mock.patch.dict(
            "sys.modules",
            {"faster_whisper": whisper_mod, "numpy": mock.MagicMock()},
        ), mock.patch.dict(CONFIG, {"STT_LANGUAGE": "en-IN"}):
            result = controller._transcribe_whisper(audio)
        self.assertEqual(result, "good morning")
        whisper_mod.WhisperModel.assert_called_once_with(
            CONFIG["WHISPER_MODEL"], device=CONFIG["WHISPER_DEVICE"], compute_type="auto"
        )

    def test_whisper_transcription_empty_on_error(self):
        controller = self._make_controller(engine="whisper")
        audio = mock.MagicMock()
        audio.get_raw_data.side_effect = OSError("no data")
        result = controller._transcribe_whisper(audio)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
