from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import os
import textwrap
from datetime import timedelta, date
from typing import Any, Dict, List, Optional

import httpx
from dateutil.parser import isoparse
from pydantic import BaseModel, Field

from fastmcp import FastMCP

OVERPASS_API = os.getenv(
    "OVERPASS_API", "https://overpass-api.de/api/interpreter")
USE_OVERPASS = os.getenv("USE_OVERPASS", "true").lower() == "true"

# 필요한 패키지: fastmcp, httpx, pydantic
# pip install fastmcp httpx pydantic


OVERPASS_API = os.getenv(
    "OVERPASS_API", "https://overpass-api.de/api/interpreter")
USE_OVERPASS = os.getenv("USE_OVERPASS", "true").lower() == "true"

mcp = FastMCP("travel-places-tools")

# ---------- 카테고리 정의 ----------


class PlaceCategory(str, Enum):
    hotel = "hotel"
    cafe = "cafe"
    restaurant = "restaurant"
    police = "police"
    airport = "airport"
    bank = "bank"
    atm = "atm"
    pharmacy = "pharmacy"
    hospital = "hospital"
    train_station = "train_station"
    bus_stop = "bus_stop"
    museum = "museum"
    park = "park"
    temple = "temple"
    market = "market"
    supermarket = "supermarket"
    bar = "bar"
    convenience = "convenience"
    viewpoint = "viewpoint"
    library = "library"


# OSM 태그 매핑
# 각 카테고리를 (key, value) 목록으로 연결. (일부는 다중 키 지원)
CATEGORY_TAGS: Dict[PlaceCategory, List[Tuple[str, str]]] = {
    # 일부 데이터는 amenity=hotel 로도 표기됨
    PlaceCategory.hotel:       [("tourism", "hotel"), ("amenity", "hotel")],
    PlaceCategory.cafe:        [("amenity", "cafe")],
    PlaceCategory.restaurant:  [("amenity", "restaurant")],
    PlaceCategory.police:      [("amenity", "police")],
    PlaceCategory.airport:     [("aeroway", "aerodrome"), ("aeroway", "airport")],
    PlaceCategory.bank:        [("amenity", "bank")],
    PlaceCategory.atm:         [("amenity", "atm")],
    PlaceCategory.pharmacy:    [("amenity", "pharmacy")],
    PlaceCategory.hospital:    [("amenity", "hospital"), ("amenity", "clinic")],
    PlaceCategory.train_station: [("railway", "station")],
    PlaceCategory.bus_stop:    [("highway", "bus_stop"), ("public_transport", "platform")],
    PlaceCategory.museum:      [("tourism", "museum")],
    PlaceCategory.park:        [("leisure", "park")],
    PlaceCategory.temple:      [("amenity", "place_of_worship"), ("building", "temple")],
    PlaceCategory.market:      [("amenity", "marketplace")],
    PlaceCategory.supermarket: [("shop", "supermarket")],
    PlaceCategory.bar:         [("amenity", "bar")],
    PlaceCategory.convenience: [("shop", "convenience")],
    PlaceCategory.viewpoint:   [("tourism", "viewpoint")],
    PlaceCategory.library:     [("amenity", "library")],
}

# ---------- 입/출력 스키마 ----------


class PlacesIn(BaseModel):
    lat: float = Field(..., description="위도")
    lon: float = Field(..., description="경도")
    categories: List[PlaceCategory] = Field(
        default=[PlaceCategory.hotel, PlaceCategory.cafe,
                 PlaceCategory.restaurant],
        description="찾을 카테고리 목록"
    )
    radius_m: int = Field(3000, ge=100, le=20000, description="검색 반경(미터)")
    limit: int = Field(20, ge=1, le=100, description="최대 반환 개수")


class Place(BaseModel):
    name: str
    category: PlaceCategory
    address: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    # 부가정보(있으면 채움)
    stars: Optional[str] = None
    opening_hours: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class PlacesOut(BaseModel):
    places: List[Place] = []

# ---------- 유틸 ----------


def _addr_from_tags(tags: Dict[str, Any]) -> str:
    parts = [tags.get(k, "") for k in (
        "addr:street", "addr:housenumber", "addr:city", "addr:district")]
    parts = [p for p in parts if p]
    return ", ".join(parts)


def _guess_category(tags: Dict[str, Any], requested: List[PlaceCategory]) -> Optional[PlaceCategory]:
    # 요청된 카테고리 중, 매칭되는 태그가 있으면 그 카테고리로 귀속
    for cat in requested:
        for k, v in CATEGORY_TAGS.get(cat, []):
            if tags.get(k) == v:
                return cat
    return None


def _build_overpass_query(lat: float, lon: float, radius: int, requested: List[PlaceCategory], limit: int) -> str:
    # ( ) 안에 여러 selector를 OR 로 묶고, node/way/relation 모두 포함
    selectors = []
    for cat in requested:
        for k, v in CATEGORY_TAGS.get(cat, []):
            # node/way/relation 각각 around:radius 적용
            selectors.append(
                f'node["{k}"="{v}"](around:{radius},{lat},{lon});')
            selectors.append(f'way["{k}"="{v}"](around:{radius},{lat},{lon});')
            selectors.append(
                f'relation["{k}"="{v}"](around:{radius},{lat},{lon});')

    # 안전장치: 요청이 비었으면 아무것도 검색하지 않음
    if not selectors:
        selectors = ['node["tourism"="hotel"](around:{r},{lat},{lon});'.format(
            r=radius, lat=lat, lon=lon)]

    body = "\n      ".join(selectors)
    # out center <limit>; : way/relation의 중심 좌표 포함, limit 적용
    q = textwrap.dedent(f"""
    [out:json][timeout:45];
    (
      {body}
    );
    out center {limit};
    """).strip()
    return q

# ---------- MCP Tool ----------


@mcp.tool()
async def find_places(input: PlacesIn) -> PlacesOut:
    """
    여행에 유용한 장소(호텔/카페/식당/경찰서/공항/은행/ATM/약국/병원/기차역/버스정류장/박물관/공원/사찰/시장/슈퍼 등)를
    Overpass API로 조회합니다. node/way/relation 모두 포함.
    USE_OVERPASS=false 면 빈 목록을 반환합니다.

    #입력 
        lat: float
        lon: float
        categories: List[PlaceCategory]
        radius_m: int
        limit: int
    #출력
        places: List[Place]
    """
    if not USE_OVERPASS:
        return PlacesOut(places=[])

    lat, lon = input.lat, input.lon
    query = _build_overpass_query(
        lat, lon, input.radius_m, input.categories, input.limit)

    places: List[Place] = []
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OVERPASS_API, data={"data": query})
        if r.status_code != 200:
            return PlacesOut(places=[])

        data = r.json() or {}
        for el in (data.get("elements") or [])[: input.limit]:
            tags: Dict[str, Any] = el.get("tags", {}) or {}
            # 좌표: node는 lat/lon, way/relation은 center.lat/center.lon
            el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
            el_lon = el.get("lon") or (el.get("center") or {}).get("lon")

            # 카테고리 추정 (요청 목록 중 태그 매칭)
            cat = _guess_category(tags, input.categories)
            if cat is None:
                # 요청 외 태그로 나왔다면 스킵(혹은 other로 잡아도 됨)
                continue

            name = tags.get("name") or "(Unnamed)"
            addr = _addr_from_tags(tags)

            place = Place(
                name=name,
                category=cat,
                address=addr,
                lat=el_lat,
                lon=el_lon,
                stars=tags.get("stars"),
                opening_hours=tags.get("opening_hours"),
                phone=tags.get("phone"),
                website=tags.get("website"),
            )
            places.append(place)

    return PlacesOut(places=places)


if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8003)
    args = parser.parse_args()

    mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
