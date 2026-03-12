from pydantic import BaseModel
import os
from typing import Any, Dict, List, Optional

import httpx

from fastmcp import FastMCP  # 간단한 MCP 서버 프레임워크

WIKI_SUMMARY = os.getenv(
    "WIKI_SUMMARY",
    "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
)
WIKI_SEARCH = os.getenv(
    "WIKI_SEARCH",
    "https://en.wikipedia.org/w/api.php"
)
WIKI_REST_SEARCH = os.getenv(
    "WIKI_REST_SEARCH",
    "https://en.wikipedia.org/api/rest_v1/search/title"
)

# 위키 요청 헤더(과도한 차단 방지 및 식별용)
HEADERS = {
    "User-Agent": os.getenv("WIKI_UA", "travel-mcp/0.1 (+https://example.local)")
}


class POI(BaseModel):
    title: str
    snippet: str = ""
    url: str = ""


class WikiOut(BaseModel):
    wiki_summary: str = ""
    pois: List[POI] = []


mcp = FastMCP("trip-wiki")


@mcp.prompt("poi_search_prompt")
def poi_search_prompt(text: str) -> str:
    """전체 위키 제목/스니펫을 바탕으로 관광 명소(indoor/outdoor/theme)를 분류 및 중복 제거.
    input : 관광 명소가 포함된 일반 텍스트
    output : 관광 명소 분류 및 중복 제거한 JSON 리스트
    """
    return f"""
        아래 장소들을 JSON으로 분류하세요.
        필드: title, type(indoor|outdoor|mixed), theme(museum|temple|park|market|neighborhood|view|food|other 중 하나),
        우선순위(1-5). 중복 항목은 병합하세요.
        입력:
        {text}
        """


@mcp.tool()
async def wiki_info(destination: str) -> WikiOut:
    """
    목적지의 위키요약과 관광 POI 후보 수집.
    # input:
     destination : 지역명을 영어 단어로 입력
    # output:
     wiki_summary : 위키요약
     pois : JSON 형식의 관광 POI 후보
    REST v1 summary → 실패 시 검색 API fallback.
    """
    dest = destination.strip()
    out_summary = ""
    pois: List[POI] = []

    async with httpx.AsyncClient(timeout=20, headers=HEADERS) as client:
        print(f"destination: {dest}")
        print(f"WIKI_SUMMARY: {WIKI_SUMMARY.format(dest)}")
        # summary
        try:
            s = await client.get(WIKI_SUMMARY.format(dest))
            if s.status_code == 200:
                out_summary = (s.json() or {}).get("extract") or ""
        except Exception:
            pass

        # 검색 (우선 MediaWiki API, 실패 시 REST title search)
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{dest} tourist attractions OR museums OR parks OR markets",
            "srlimit": 12,
            "format": "json",
        }
        try:
            q = await client.get(WIKI_SEARCH, params=params)
            if q.status_code == 200:
                hits = (q.json() or {}).get(
                    "query", {}).get("search", []) or []
                for h in hits[:10]:
                    title = h.get("title")
                    pois.append(POI(
                        title=title or "",
                        snippet=h.get("snippet", ""),
                        url=f"https://en.wikipedia.org/wiki/{title}",
                    ))
            else:
                r = await client.get(WIKI_REST_SEARCH, params={"q": dest, "limit": 12})
                if r.status_code == 200:
                    for item in ((r.json() or {}).get("pages") or [])[:10]:
                        title = item.get("title")
                        pois.append(POI(
                            title=title or "",
                            snippet=item.get("description", "") or "",
                            url=f"https://en.wikipedia.org/wiki/{title}",
                        ))
        except Exception:
            pass

    return WikiOut(wiki_summary=out_summary, pois=pois)


if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    # FastMCP 예시
    # mcp.run_http(host="0.0.0.0", port=args.port, path="/mcp")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)
