import unittest
from unittest import mock

import requests

from keerthi.services.weather import fetch_weather, geocode


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class TestGeocode(unittest.TestCase):
    def test_geocode_returns_first_result(self):
        with mock.patch("keerthi.services.weather.requests.get") as get:
            get.return_value = FakeResponse(
                {"results": [{"name": "Hyderabad", "latitude": 17.38, "longitude": 78.48}]}
            )
            place = geocode("Hyderabad")
        self.assertEqual(place["name"], "Hyderabad")
        self.assertAlmostEqual(place["latitude"], 17.38)

    def test_geocode_raises_when_no_results(self):
        with mock.patch("keerthi.services.weather.requests.get") as get:
            get.return_value = FakeResponse({"results": []})
            with self.assertRaises(LookupError):
                geocode("nowhere, antarctica")


class TestFetchWeather(unittest.TestCase):
    def _mock_requests(self, geo_payload, forecast_payload):
        def side_effect(url, **_):
            if "geocoding" in url:
                return FakeResponse(geo_payload)
            return FakeResponse(forecast_payload)

        patcher = mock.patch("keerthi.services.weather.requests.get", side_effect=side_effect)
        return patcher

    def test_fetch_weather_success(self):
        geo = {"results": [{"name": "Hyderabad", "latitude": 17.38, "longitude": 78.48}]}
        forecast = {
            "current": {
                "temperature_2m": 31.5,
                "weather_code": 2,
                "wind_speed_10m": 12.0,
            }
        }
        with self._mock_requests(geo, forecast):
            result = fetch_weather("Hyderabad")
        self.assertIn("Hyderabad", result)
        self.assertIn("31.5°C", result)
        self.assertIn("partly cloudy", result)
        self.assertIn("12.0 km/h", result)

    def test_fetch_weather_location_not_found(self):
        with self._mock_requests({"results": []}, {}):
            result = fetch_weather("atlantis")
        self.assertEqual(result, "I couldn't retrieve the weather right now.")

    def test_fetch_weather_request_error(self):
        with mock.patch(
            "keerthi.services.weather.requests.get",
            side_effect=requests.RequestException("boom"),
        ):
            result = fetch_weather("Hyderabad")
        self.assertEqual(result, "I couldn't retrieve the weather right now.")


if __name__ == "__main__":
    unittest.main()
