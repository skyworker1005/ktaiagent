import os
import textwrap
from datetime import timedelta, date
from typing import Any, Dict, List, Optional

import httpx
from dateutil.parser import isoparse
from pydantic import BaseModel, Field

from fastmcp import FastMCP  # 간단한 MCP 서버 프레임워크

OPEN_METEO_GEOCODE = os.getenv(
    "OPEN_METEO_GEOCODE", "https://geocoding-api.open-meteo.com/v1/search")


mcp = FastMCP("geocode")


@mcp.tool()
async def get_geocode(destination: str) -> Dict[str, Any]:
    """
    위도/경도/타임존 조회. 
    input : 지역명을 영어 단어로 입력
    output : 위도, 경도, 타임존
    내부적으로 Open-Meteo Geocoding API 사용.
    """

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            OPEN_METEO_GEOCODE,
            params={"name": destination, "count": 1, "language": "en"},
        )
        r.raise_for_status()
        results = (r.json() or {}).get("results") or []
        if not results:
            raise RuntimeError("Destination not found")

        top = results[0]
        lat, lon = float(top["latitude"]), float(top["longitude"])
        tz = top.get("timezone") or "UTC"

    return {"lat": lat, "lon": lon, "tz": tz}

if __name__ == "__main__":
    mcp.run(transport="stdio")
