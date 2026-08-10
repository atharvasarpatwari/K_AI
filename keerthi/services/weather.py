import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm with hail",
}


def geocode(location: str) -> dict[str, Any]:
    """Resolves a place name to its coordinates via the Open-Meteo geocoder."""
    response = requests.get(
        GEOCODING_URL,
        params={"name": location, "count": "1", "language": "en", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise LookupError(f"Could not locate '{location}'")
    return dict(results[0])


def fetch_weather(location: str) -> str:
    """Returns a human-readable current-weather summary for `location`."""
    try:
        place = geocode(location)
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": str(place["latitude"]),
                "longitude": str(place["longitude"]),
                "current": "temperature_2m,weather_code,wind_speed_10m",
            },
            timeout=10,
        )
        response.raise_for_status()
        current = response.json()["current"]
        temp = current["temperature_2m"]
        wind = current["wind_speed_10m"]
        code = current.get("weather_code", 0)
        description = WEATHER_CODES.get(code, "unknown conditions")
        name = place.get("name", location)
        return f"Weather in {name}: {temp}°C, {description}, wind {wind} km/h."
    except (LookupError, requests.RequestException, KeyError, ValueError):
        logger.exception("Weather lookup failed")
        return "I couldn't retrieve the weather right now."
