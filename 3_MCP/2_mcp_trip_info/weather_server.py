import os
import textwrap
from datetime import timedelta, date
from typing import Any, Dict, List, Optional

import httpx
from dateutil.parser import isoparse
from pydantic import BaseModel, Field

from fastmcp import FastMCP

OPEN_METEO_FORECAST = os.getenv(
    "OPEN_METEO_FORECAST", "https://api.open-meteo.com/v1/forecast")


def _fmt_day(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _iso_to_date(s: str) -> date:
    return isoparse(s).date()


mcp = FastMCP("trip-weather")


@mcp.tool()
async def weather_forecast(lat: float, lon: float, tz: str, start_date: str, nights: int = 1) -> dict:
    """
    여행 기간의 시간대/일별 날씨(기온/강수/풍속 등)를 Open-Meteo Forecast API로 조회.

    # 입력 
    - lat(float): 위도
    - lon(float): 경도
    - tz(str): 타임존
    - start_date(str): 여행 시작일 ISO8601 (YYYY-MM-DD)
    - nights(int): 숙박 일수(최소 1)

    # 출력
    - weather(dict): 날씨 정보
    """
    start = _iso_to_date(start_date)
    end = start + timedelta(days=max(1, nights))
    today = date.today()
    # Forecast API는 오늘~최대 16일만 지원. 과거/너무 먼 미래는 오늘 기준으로 보정
    start = max(today, min(start, today + timedelta(days=16)))
    end = min(today + timedelta(days=16), max(end, start))
    if start > end:
        end = start

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "precipitation", "windspeed_10m"],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_hours",
        ],
        "timezone": tz,
        "start_date": _fmt_day(start),
        "end_date": _fmt_day(end),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        f = await client.get(OPEN_METEO_FORECAST, params=params)
        f.raise_for_status()
        data = f.json()

    return data


if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()

    # FastMCP 예시
    mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
