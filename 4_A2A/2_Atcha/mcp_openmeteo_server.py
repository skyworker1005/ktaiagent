import math
from typing import Dict, Any, Optional
import asyncio

import httpx
from fastmcp import FastMCP

mcp = FastMCP(name="open_meteo_tools")

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"

async def _geocode(client: httpx.AsyncClient, city: str, lang: str = "ko") -> Optional[Dict[str, Any]]:
    r = await client.get(GEOCODE, params={"name": city, "count": 1, "language": lang}, timeout=20)
    r.raise_for_status()
    js = r.json()
    results = js.get("results") or []
    return results[0] if results else None

async def _forecast(client: httpx.AsyncClient, lat: float, lon: float, days: int, tz: str = "Asia/Seoul") -> Dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,cloudcover,uv_index,wind_speed_10m",
        "timezone": tz,
        "forecast_days": days
    }
    r = await client.get(FORECAST, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _daily_summary(hourly: Dict[str, Any]) -> Dict[str, Any]:
    times = hourly.get("time") or []
    temp = hourly.get("temperature_2m") or []
    precip = hourly.get("precipitation") or []
    cloud = hourly.get("cloudcover") or []
    uv = hourly.get("uv_index") or []
    wind = hourly.get("wind_speed_10m") or []

    n = min(len(times), len(temp), len(precip), len(cloud), len(uv), len(wind))
    if n == 0:
        return {}

    days: Dict[str, Dict[str, Any]] = {}
    for i in range(n):
        day = str(times[i])[:10]  # YYYY-MM-DD
        bucket = days.setdefault(day, {"temp": [], "precip": [], "cloud": [], "uv": [], "wind": []})
        bucket["temp"].append(temp[i])
        bucket["precip"].append(precip[i])
        bucket["cloud"].append(cloud[i])
        bucket["uv"].append(uv[i])
        bucket["wind"].append(wind[i])

    out: Dict[str, Any] = {}
    for day, b in days.items():
        out[day] = {
            "temp_min": float(min(b["temp"])) if b["temp"] else None,
            "temp_max": float(max(b["temp"])) if b["temp"] else None,
            "precip_sum": float(sum(b["precip"])) if b["precip"] else 0.0,
            "cloud_mean": (float(sum(b["cloud"])) / len(b["cloud"])) if b["cloud"] else None,
            "uv_max": float(max(b["uv"])) if b["uv"] else None,
            "wind_mean": (float(sum(b["wind"])) / len(b["wind"])) if b["wind"] else None,
        }
    return out

@mcp.tool
async def weather_fetch(city: str, days: int = 1, lang: str = "ko") -> Dict[str, Any]:
    """
    도시명을 받아 Open-Meteo로 날씨를 조회합니다.
    Args:
      city: 도시명 (예: "서울")
      days: 예보 일수 (1~3 권장)
      lang: 지오코딩 언어(ko/en/...)
    Returns:
      {
        "ok": true,
        "city": "...",
        "latitude": 37.5,
        "longitude": 127.0,
        "timezone": "Asia/Seoul",
        "hourly": {...},          # Open-Meteo hourly
        "daily": { "YYYY-MM-DD": {
            "temp_min": ...,
            "temp_max": ...,
            "precip_sum": ...,
            "cloud_mean": ...,
            "uv_max": ...,
            "wind_mean": ...
        }, ...}
      }
    """
    if days < 1 or days > 5:
        raise ValueError("days must be 1..5")

    async with httpx.AsyncClient() as client:
        geo = await _geocode(client, city, lang=lang)
        if not geo:
            return {"ok": False, "error": f"city not found: {city}"}
        lat = float(geo["latitude"]); lon = float(geo["longitude"])
        fc = await _forecast(client, lat, lon, days)
    hourly = fc.get("hourly") or {}
    return {
        "ok": True,
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "timezone": fc.get("timezone", "Asia/Seoul"),
        "hourly": hourly,
        "daily": _daily_summary(hourly)
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8001)
