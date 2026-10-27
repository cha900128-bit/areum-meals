#!/usr/bin/env python3
"""Collect Areum High School meals for a GitHub Pages static site.

Runs on GitHub Actions; no web request is made by the reader's browser.
Uses NEIS per-day requests and a secondary publicly accessible menu endpoint.
An optional NEIS_API_KEY GitHub Actions secret can be provided.
"""
from __future__ import annotations

import concurrent.futures
from datetime import date, datetime, timedelta, timezone
import html
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCHOOL_NAME = "세종시 아름고등학교"
SCHOOL_CODE = "9300117"
OFFICE_CODE = "I10"
KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "data" / "meals.json"

# Previously checked October data are a clearly labelled local fallback, not live data.
BACKUP = {
    "20261026": {
        "2": ["닭갈비김치덮밥", "모닝빵샌드위치", "미역장국", "고구마줄기볶음(자율)", "스틱김자반", "총각김치", "레몬에이드"],
        "3": ["추가밥&도시락김(self)", "대만식탄탄멘", "카프레제샐러드(자율)", "후라이드닭꼬치", "포기김치", "얇은단무지", "빠삐코"],
    },
    "20261027": {
        "2": ["돈까스김밥", "사골미역국", "취나물무침(자율)", "볶음김치", "가지라쟈냐", "쁘띠첼(밀감)"],
    },
    "20261028": {
        "2": ["추가밥&도시락김(self)", "양지쌀국수", "그린샐러드&파인애플드레싱(자율)", "양파초절임(자율)", "통새우짜조롤&칠리소스", "포기김치", "사과", "덴마크드링킹요구르트(딸기)"],
        "3": ["치킨마요덮밥", "얼큰소고기무국", "그린샐러드&딸기드레싱(자율)", "떡볶이", "오징어링튀김&케첩", "깍두기", "짜요짜요(포도)"],
    },
    "20261029": {
        "2": ["발아현미밥", "버섯불고기", "감자국", "삼치카레구이", "깍두기", "배추겉절이(자율)", "아이스슈"],
        "3": ["혼합잡곡밥", "모둠어묵국", "계란장조림", "볶음김치", "미역줄기볶음(자율)", "고구마치즈돈까스&브라운소스", "초코칩트위스트도넛"],
    },
    "20261030": {
        "2": ["찹쌀밥", "돼지국밥&다대기(셀프)", "아삭이된장무침(자율)", "아비꼬고로케&케첩", "섞박지", "쇼콜라크레이프케이크"],
    },
}


def clean_dish(value: object) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()
    # NEIS appends allergy labels, e.g. 떡볶이1.2.5.6.13.
    text = re.sub(r"\s*(?:\d{1,2}\.){1,16}\s*$", "", text).strip()
    return text


def request_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (AreumSchoolMeals/1.0)", "Accept": "application/json"})
    with urlopen(req, timeout=10) as resp:
        if not 200 <= resp.status < 300:
            raise ValueError(f"HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8-sig"))


def meals_from_neis(payload: dict, target: str) -> dict[str, list[str]]:
    sections = payload.get("mealServiceDietInfo", []) if isinstance(payload, dict) else []
    rows = [row for block in sections for row in block.get("row", [])] if isinstance(sections, list) else []
    result: dict[str, list[str]] = {}
    for row in rows:
        if str(row.get("MLSV_YMD", "")) != target:
            continue
        kind = str(row.get("MMEAL_SC_CODE", ""))
        if kind not in ("2", "3"):
            continue
        pieces = re.split(r"<br\s*/?>|\r?\n", str(row.get("DDISH_NM") or ""), flags=re.IGNORECASE)
        items = [x for chunk in pieces if (x := clean_dish(chunk))]
        if items:
            result[kind] = items
    return result


def meals_from_alt(payload: dict, target: str) -> dict[str, list[str]]:
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    result: dict[str, list[str]] = {}
    if not isinstance(rows, list):
        return result
    for row in rows:
        if str(row.get("date", "")).replace("-", "") != target:
            continue
        rtype = row.get("type") or {}
        kind = str(rtype.get("code", "")) if isinstance(rtype, dict) else ""
        if not kind and isinstance(rtype, dict):
            kind = {"중식": "2", "석식": "3"}.get(rtype.get("name", ""), "")
        if kind not in ("2", "3"):
            continue
        items = []
        for item in row.get("menu", []):
            val = item if isinstance(item, str) else item.get("name", "") if isinstance(item, dict) else ""
            if clean_dish(val):
                items.append(clean_dish(val))
        if items:
            result[kind] = items
    return result


def get_day(day: date) -> tuple[str, dict[str, list[str]], str]:
    key = day.strftime("%Y%m%d")
    if os.getenv("MEALS_OFFLINE") == "1":
        return key, {}, "offline"
    p = {
        "Type": "json", "pIndex": "1", "pSize": "20",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": key,
    }
    if os.getenv("NEIS_API_KEY"):
        p["KEY"] = os.environ["NEIS_API_KEY"]
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo?" + urlencode(p)
    try:
        payload = request_json(url)
        found = meals_from_neis(payload, key)
        if found:
            return key, found, "나이스"
    except Exception:
        pass
    try:
        url = "https://kschoolinfo.com/api/v1/meals?" + urlencode({
            "eduCode": OFFICE_CODE, "schoolCode": SCHOOL_CODE, "date": key,
        })
        payload = request_json(url)
        found = meals_from_alt(payload, key)
        if found:
            return key, found, "학교급식정보"
    except Exception:
        pass
    return key, {}, "미등록/조회실패"


def main() -> None:
    now = datetime.now(KST)
    first = now.date() - timedelta(days=7)
    days = [first + timedelta(days=offset) for offset in range(43)]
    # Most school lunch services have no weekend meal; retain backup weekends if supplied.
    days = [d for d in days if d.weekday() < 5]
    collected: dict[str, dict[str, list[str]]] = {}
    sources: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for key, items, origin in pool.map(get_day, days):
            if items:
                collected[key] = items
                sources[key] = origin
    # Backups never override a newly fetched menu.
    for key, saved in BACKUP.items():
        if first.strftime("%Y%m%d") <= key <= days[-1].strftime("%Y%m%d"):
            if key not in collected:
                collected[key] = saved
                sources[key] = "이전 확인 식단 (실시간 아님)"
    payload = {
        "school": SCHOOL_NAME,
        "generated_at": now.isoformat(timespec="seconds"),
        "range": [first.isoformat(), (first + timedelta(days=42)).isoformat()],
        "meals": dict(sorted(collected.items())),
        "sources": sources,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}: {len(collected)} dates with meals, {len(days)} school days checked")
    if not collected:
        print("WARNING: API returned no school meals. Site will show a clear availability message.")


if __name__ == "__main__":
    main()
