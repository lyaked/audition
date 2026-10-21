"""필름메이커스 배우모집 공고를 가져와서 내 조건(남자, 32세)에 맞는 것만 골라 index.html로 만든다."""
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

MY_AGE = 32
MY_GENDER = "남자"
PAGES = 5  # 한 페이지에 약 20개
BASE = "https://www.filmmakers.co.kr/actorCasting"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
OUT = Path(__file__).with_name("index.html")
TEMPLATE = Path(__file__).with_name("template.html")

KST = dt.timezone(dt.timedelta(hours=9))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


CARD_RE = re.compile(r"<span class=\"member_\d+ hidden\"></span>(.*?)(?=<span class=\"member_\d+ hidden\"></span>|<nav)", re.S)
FIELD_RE = re.compile(r'text-xs font-medium text-sub truncate">([^<]*)</div>\s*<div class="text-sm truncate[^"]*">([^<]*)</div>')


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def parse_cards(page_html):
    posts = []
    for m in CARD_RE.finditer(page_html):
        block = m.group(1)
        link = re.search(r'<a href="(https://www\.filmmakers\.co\.kr/actorCasting/(\d+))"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        badges = [clean(b) for b in re.findall(r'<span class="px-2 py-0\.5 text-xs[^"]*rounded">([^<]*)</span>', block)]
        date = re.search(r'text-xs text-sub">(\d{4}-\d{2}-\d{2} \d{2}:\d{2})<', block)
        fields = {clean(k): clean(v) for k, v in FIELD_RE.findall(block)}
        posts.append({
            "id": link.group(2),
            "url": link.group(1),
            "headline": clean(link.group(3)),
            "category": next((b for b in badges if b != "바로지원"), ""),
            "direct": "바로지원" in badges,
            "posted": date.group(1) if date else "",
            "producer": fields.get("제작", ""),
            "work": fields.get("제목", ""),
            "gender": fields.get("성별", ""),
            "age": fields.get("연령", ""),
            "pay": fields.get("출연료", ""),
            "deadline": fields.get("마감", ""),
        })
    return posts


def age_bounds(label):
    """'20대 중반' -> (24, 26), '아역(13세 미만)' -> (0, 12). 모르는 형식이면 None."""
    label = label.strip()
    if label.startswith("아역"):
        return 0, 12
    m = re.match(r"(\d+)대\s*(초반|중반|후반)?", label)
    if not m:
        return None
    d = int(m.group(1))
    part = {"초반": (0, 3), "중반": (4, 6), "후반": (7, 9)}.get(m.group(2), (0, 9))
    return d + part[0], d + part[1]


def age_ok(age):
    if not age or "무관" in age:
        return True
    parts = [p for p in re.split(r"~", age) if p.strip()]
    lo_b, hi_b = age_bounds(parts[0]), age_bounds(parts[-1])
    if lo_b is None or hi_b is None:
        return True  # 형식을 모르면 일단 보여준다
    return lo_b[0] <= MY_AGE <= hi_b[1]


def gender_ok(gender):
    return not gender or MY_GENDER in gender or "무관" in gender


def main():
    today = dt.datetime.now(KST).date().isoformat()
    seen, posts = set(), []
    for page in range(1, PAGES + 1):
        url = BASE if page == 1 else f"{BASE}/page/{page}"
        for p in parse_cards(fetch(url)):
            if p["id"] not in seen:
                seen.add(p["id"])
                posts.append(p)
    if not posts:
        sys.exit("공고를 하나도 못 읽었어요. 사이트 구조가 바뀌었을 수 있어요.")
    matched = [p for p in posts
               if gender_ok(p["gender"]) and age_ok(p["age"])
               and (not p["deadline"] or p["deadline"] >= today)]
    data = {
        "updated": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "scanned": len(posts),
        "posts": matched,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload), encoding="utf-8")
    print(f"{len(posts)}개 중 {len(matched)}개 통과 -> {OUT.name}")


if __name__ == "__main__":
    main()
