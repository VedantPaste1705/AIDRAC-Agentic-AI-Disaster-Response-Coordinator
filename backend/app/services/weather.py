import httpx
from typing import Optional
from app.config.settings import settings
from app.utils.latency import LatencyTracker


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5"

    async def get_current_weather(self, lat: float, lng: float, _tracker: Optional[LatencyTracker] = None) -> dict:
        if _tracker:
            _tracker.start("weather_api_call")
        
        if not settings.OPENWEATHER_API_KEY:
            if _tracker:
                _tracker.end("weather_api_call", {"error": "api_key_missing"})
            raise ValueError("OpenWeather API key not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/weather",
                params={
                    "lat": lat,
                    "lon": lng,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            data = response.json()
            rain = 0
            if "rain" in data:
                rain = data["rain"].get("1h", data["rain"].get("3h", 0))
            result = {
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "rain": rain,
                "icon": data["weather"][0]["icon"],
                "city": data["name"],
            }
        
        if _tracker:
            _tracker.end("weather_api_call")
        return result
