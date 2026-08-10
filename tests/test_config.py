import os
import unittest
import warnings
from unittest import mock

import keerthi.config as cfg


class TestValidateConfig(unittest.TestCase):
    def setUp(self):
        self._original = dict(cfg.CONFIG)

    def tearDown(self):
        cfg.CONFIG.clear()
        cfg.CONFIG.update(self._original)

    def _set_valid(self):
        cfg.CONFIG["GEMINI_API_KEY"] = "test-key"
        cfg.CONFIG["LOG_LEVEL"] = "INFO"
        cfg.CONFIG["TEMPERATURE"] = 0.7
        cfg.CONFIG["MAX_OUTPUT_TOKENS"] = 1024
        cfg.CONFIG["MAX_HISTORY_TURNS"] = 10
        cfg.CONFIG["TTS_RATE"] = 175

    def _collect_warnings(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cfg.validate_config()
        return caught

    def test_valid_config_no_warnings(self):
        self._set_valid()
        self.assertEqual(self._collect_warnings(), [])

    def test_default_model_is_not_retired(self):
        self.assertFalse(cfg.CONFIG["MODEL_NAME"].startswith(("gemini-1.5", "gemini-2.0-flash")))

    def test_retired_model_warns(self):
        self._set_valid()
        cfg.CONFIG["MODEL_NAME"] = "gemini-1.5-flash"
        self.assertTrue(self._collect_warnings())

    def test_missing_api_key_warns(self):
        self._set_valid()
        cfg.CONFIG["GEMINI_API_KEY"] = None
        self.assertTrue(self._collect_warnings())

    def test_bad_log_level_warns(self):
        self._set_valid()
        cfg.CONFIG["LOG_LEVEL"] = "BOGUS"
        self.assertTrue(self._collect_warnings())

    def test_temperature_out_of_range_warns(self):
        self._set_valid()
        cfg.CONFIG["TEMPERATURE"] = 5.0
        self.assertTrue(self._collect_warnings())

    def test_negative_output_tokens_warns(self):
        self._set_valid()
        cfg.CONFIG["MAX_OUTPUT_TOKENS"] = -1
        self.assertTrue(self._collect_warnings())

    def test_tts_rate_out_of_range_warns(self):
        self._set_valid()
        cfg.CONFIG["TTS_RATE"] = 10
        self.assertTrue(self._collect_warnings())


class TestEnvHelpers(unittest.TestCase):
    def test_env_bool_truthy_values(self):
        with mock.patch.dict(os.environ, {"X": "true"}):
            self.assertTrue(cfg._env_bool("X", False))
        with mock.patch.dict(os.environ, {"X": "1"}):
            self.assertTrue(cfg._env_bool("X", False))

    def test_env_bool_falsy_and_default(self):
        with mock.patch.dict(os.environ, {"X": "no"}):
            self.assertFalse(cfg._env_bool("X", True))
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(cfg._env_bool("MISSING", False))

    def test_env_int_valid_and_fallback(self):
        with mock.patch.dict(os.environ, {"X": "200"}):
            self.assertEqual(cfg._env_int("X", 175), 200)
        with mock.patch.dict(os.environ, {"X": "abc"}):
            self.assertEqual(cfg._env_int("X", 175), 175)


if __name__ == "__main__":
    unittest.main()
