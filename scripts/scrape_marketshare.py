#!/usr/bin/env python3
"""
Fetch brand market-share rankings from Statcounter Global Stats CSVs.

Markets and categories are driven by src/config/markets.json (shared with Astro).
Never invents figures. Skips market/category pairs that fail to fetch.
yoyChange stays null unless the prior-year month CSV is also fetched successfully.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "data"
MARKETS_PATH = ROOT / "src" / "config" / "markets.json"

USER_AGENT = (
    "GlobalMarketShareBot/1.0 "
    "(+https://xmarketshare.com; "
    "research; contact: github.com/bisonel-com/marketshare-africa)"
)
REQUEST_SLEEP_SEC = 1.5
MIN_SHARE = 0.1
MAX_RANKINGS = 10
MIN_RANKINGS = 3

PHONE_META: dict[str, tuple[str, str]] = {
    "tecno": ("Transsion Holdings", "Budget / Mid-Range"),
    "infinix": ("Transsion Holdings", "Budget / Gaming"),
    "itel": ("Transsion Holdings", "Ultra-Budget"),
    "samsung": ("Samsung Electronics", "All Tiers / Galaxy A & S"),
    "xiaomi": ("Xiaomi Corporation", "Value / Redmi Series"),
    "apple": ("Apple Inc.", "Premium / Flagship"),
    "oppo": ("BBK Electronics", "Mid-Range / Reno"),
    "vivo": ("BBK Electronics", "Mid-Range"),
    "realme": ("BBK Electronics", "Value / Youth"),
    "huawei": ("Huawei Technologies", "Mid / Premium"),
    "motorola": ("Lenovo Group", "Mid-Range"),
    "google": ("Alphabet Inc.", "Premium / Pixel"),
    "nokia": ("HMD Global", "Budget / Feature & Smart"),
    "honor": ("Honor Device Co.", "Mid-Range"),
    "oneplus": ("BBK Electronics", "Premium / Flagship"),
    "hmd": ("HMD Global", "Budget / Feature & Smart"),
    "zte": ("ZTE Corporation", "Budget"),
    "bbk": ("BBK Electronics", "Multi-Brand"),
}

BROWSER_META: dict[str, tuple[str, str]] = {
    "chrome": ("Google", "Desktop & Mobile"),
    "safari": ("Apple", "iOS & macOS"),
    "opera": ("Opera Norway / Opera Ltd", "Mobile & Desktop"),
    "edge": ("Microsoft", "Desktop & Mobile"),
    "edge legacy": ("Microsoft", "Legacy Desktop"),
    "samsung internet": ("Samsung", "Android Mobile"),
    "firefox": ("Mozilla", "Desktop & Mobile"),
    "uc browser": ("Alibaba (UCWeb)", "Mobile"),
    "brave": ("Brave Software", "Privacy Browser"),
    "yandex browser": ("Yandex", "Desktop & Mobile"),
    "phoenix": ("Phoenix Browser", "Mobile"),
    "android": ("Google", "WebView / System"),
}

DROP_BRANDS = {"other", "unknown"}

DATA_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "slug",
        "scope",
        "market",
        "marketSlug",
        "marketCode",
        "category",
        "categorySlug",
        "period",
        "lastUpdated",
        "sourceName",
        "sourceUrl",
        "methodologyNote",
        "aiSummary",
        "faqs",
        "rankings",
    ],
    "properties": {
        "slug": {"type": "string", "minLength": 3},
        "scope": {"type": "string", "enum": ["worldwide", "region", "country"]},
        "market": {"type": "string"},
        "marketSlug": {"type": "string"},
        "marketCode": {"type": "string"},
        "category": {"type": "string"},
        "categorySlug": {"type": "string"},
        "period": {"type": "string"},
        "lastUpdated": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "sourceName": {"type": "string"},
        "sourceUrl": {"type": "string"},
        "methodologyNote": {"type": "string"},
        "aiSummary": {"type": "string", "minLength": 20},
        "faqs": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["question", "answer"],
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "rankings": {
            "type": "array",
            "minItems": MIN_RANKINGS,
            "maxItems": MAX_RANKINGS,
            "items": {
                "type": "object",
                "required": [
                    "rank",
                    "brand",
                    "parentCompany",
                    "sharePercent",
                    "yoyChange",
                    "segment",
                    "highlight",
                ],
                "properties": {
                    "rank": {"type": "integer", "minimum": 1},
                    "brand": {"type": "string"},
                    "parentCompany": {"type": "string"},
                    "sharePercent": {"type": "number", "exclusiveMinimum": 0},
                    "yoyChange": {"type": ["number", "null"]},
                    "segment": {"type": "string"},
                    "highlight": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        # Backward-compatible aliases for country pages
        "country": {"type": "string"},
        "countryCode": {"type": "string"},
    },
    "additionalProperties": False,
}


def load_markets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = json.loads(MARKETS_PATH.read_text(encoding="utf-8"))
    markets: list[dict[str, Any]] = [raw["worldwide"], *raw["regions"], *raw["countries"]]
    categories: list[dict[str, Any]] = raw["categories"]
    return markets, categories


def month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%B %Y")


def month_ints(year: int, month: int) -> tuple[str, str]:
    return f"{year}{month:02d}", f"{year}-{month:02d}"


def previous_complete_month(today: date | None = None) -> tuple[int, int]:
    today = today or date.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def build_csv_url(
    market: dict[str, Any],
    category: dict[str, Any],
    year: int,
    month: int,
) -> str:
    yyyymm, yyyy_mm = month_ints(year, month)
    params = {
        **category["params"],
        "region_hidden": market["code"],
        "granularity": "monthly",
        "region": market["statcounterRegion"],
        "fromInt": yyyymm,
        "toInt": yyyymm,
        "fromMonthYear": yyyy_mm,
        "toMonthYear": yyyy_mm,
        "csv": "1",
    }
    return "https://gs.statcounter.com/chart.php?" + urllib.parse.urlencode(params)


def source_page_url(market: dict[str, Any], category: dict[str, Any]) -> str:
    # Statcounter uses continent/country slugs; worldwide has no trailing slug segment.
    if market["scope"] == "worldwide":
        return f"https://gs.statcounter.com/{category['sourcePath']}"
    return f"https://gs.statcounter.com/{category['sourcePath']}/{market['slug']}"


def fetch_csv(url: str, session: requests.Session) -> str:
    resp = session.get(url, timeout=45)
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or "<html" in text[:200].lower():
        raise ValueError(f"Non-CSV response from {url}")
    return text


def parse_share_csv(text: str) -> tuple[str | None, list[tuple[str, float]]]:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return None, []
    header = rows[0]
    period_hint = None
    if len(header) >= 2 and "(" in header[1] and ")" in header[1]:
        period_hint = header[1].split("(")[-1].rstrip(")")
    entries: list[tuple[str, float]] = []
    for row in rows[1:]:
        if len(row) < 2:
            continue
        brand = row[0].strip().strip('"')
        try:
            share = float(row[1].strip().strip('"'))
        except ValueError:
            continue
        entries.append((brand, share))
    return period_hint, entries


def brand_meta(brand: str, chart_kind: str) -> tuple[str, str]:
    key = brand.strip().lower()
    if chart_kind == "browser":
        return BROWSER_META.get(key, ("Independent", "Consumer Market"))
    return PHONE_META.get(key, ("Independent / Listed", "Consumer Market"))


def filter_rankings(
    entries: list[tuple[str, float]],
    prior: dict[str, float] | None,
    chart_kind: str,
) -> list[dict[str, Any]]:
    cleaned: list[tuple[str, float]] = []
    for brand, share in entries:
        if brand.strip().lower() in DROP_BRANDS:
            continue
        if share <= MIN_SHARE:
            continue
        cleaned.append((brand, share))
    cleaned.sort(key=lambda x: (-x[1], x[0].lower()))
    cleaned = cleaned[:MAX_RANKINGS]
    rankings: list[dict[str, Any]] = []
    for i, (brand, share) in enumerate(cleaned, start=1):
        parent, segment = brand_meta(brand, chart_kind)
        yoy = None
        if prior is not None and brand in prior:
            yoy = round(share - prior[brand], 2)
        rankings.append(
            {
                "rank": i,
                "brand": brand,
                "parentCompany": parent,
                "sharePercent": round(share, 2),
                "yoyChange": yoy,
                "segment": segment,
                "highlight": i == 1,
            }
        )
    return rankings


def openai_summaries(payload_base: dict[str, Any]) -> tuple[str, list[dict[str, str]]] | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        brands = ", ".join(
            f"{r['brand']} {r['sharePercent']}%" for r in payload_base["rankings"][:5]
        )
        prompt = (
            "Write a 2-sentence factual summary and 3 FAQ Q&As based ONLY on these "
            f"Statcounter figures for {payload_base['category']} in "
            f"{payload_base['market']} ({payload_base['period']}): {brands}. "
            "Do not invent demand, growth, or strategy claims. "
            "Return JSON with keys aiSummary (string) and faqs "
            "(array of {question, answer})."
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        summary = str(data.get("aiSummary", "")).strip()
        faqs = data.get("faqs") or []
        if len(summary) < 20 or len(faqs) < 2:
            return None
        clean_faqs = [
            {
                "question": str(f["question"]).strip(),
                "answer": str(f["answer"]).strip(),
            }
            for f in faqs
            if isinstance(f, dict) and f.get("question") and f.get("answer")
        ]
        if len(clean_faqs) < 2:
            return None
        return summary, clean_faqs[:4]
    except Exception as exc:  # noqa: BLE001
        print(f"  OpenAI fallback: {exc}", file=sys.stderr)
        return None


def deterministic_summary_and_faqs(
    market: str,
    category: str,
    period: str,
    rankings: list[dict[str, Any]],
    source_url: str,
) -> tuple[str, list[dict[str, str]]]:
    top = rankings[0]
    second = rankings[1] if len(rankings) > 1 else None
    third = rankings[2] if len(rankings) > 2 else None
    parts = [
        f"In {period}, {top['brand']} led {category.lower()} market share in {market} "
        f"at {top['sharePercent']}% according to Statcounter Global Stats."
    ]
    if second and third:
        parts.append(
            f"{second['brand']} ranked second at {second['sharePercent']}%, "
            f"followed by {third['brand']} at {third['sharePercent']}%."
        )
    elif second:
        parts.append(f"{second['brand']} ranked second at {second['sharePercent']}%.")
    summary = " ".join(parts)

    faqs = [
        {
            "question": f"Which brand leads {category.lower()} market share in {market}?",
            "answer": (
                f"{top['brand']} leads with {top['sharePercent']}% share in {period}, "
                f"based on Statcounter Global Stats ({source_url})."
            ),
        },
        {
            "question": f"How is {category.lower()} market share measured for {market}?",
            "answer": (
                "Figures come from Statcounter Global Stats monthly CSV downloads. "
                "They reflect measured network traffic, not survey estimates or sales units."
            ),
        },
        {
            "question": f"What are the top three {category.lower()} brands in {market}?",
            "answer": (
                ", ".join(f"{r['brand']} ({r['sharePercent']}%)" for r in rankings[:3])
                + f" in {period}."
            ),
        },
    ]
    return summary, faqs


def validate_payload(payload: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(DATA_SCHEMA)
    Draft202012Validator(DATA_SCHEMA).validate(payload)


def write_payload(market: dict[str, Any], category_slug: str, payload: dict[str, Any]) -> Path:
    # Layout: worldwide/, region/<slug>/, <country-slug>/
    if market["scope"] == "worldwide":
        out_dir = DATA_DIR / "worldwide"
    elif market["scope"] == "region":
        out_dir = DATA_DIR / "region" / market["slug"]
    else:
        out_dir = DATA_DIR / market["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{category_slug}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_month_shares(
    session: requests.Session,
    market: dict[str, Any],
    category: dict[str, Any],
    year: int,
    month: int,
) -> tuple[str, list[tuple[str, float]], str]:
    url = build_csv_url(market, category, year, month)
    text = fetch_csv(url, session)
    period_hint, entries = parse_share_csv(text)
    if not entries:
        raise ValueError(
            f"Empty CSV for {market['name']} / {category['name']} {year}-{month:02d}"
        )
    return url, entries, period_hint or month_label(year, month)


def scrape_one(
    session: requests.Session,
    market: dict[str, Any],
    category: dict[str, Any],
    year: int,
    month: int,
) -> dict[str, Any]:
    _csv_url, entries, _hint = load_month_shares(session, market, category, year, month)
    period = month_label(year, month)

    prior_map: dict[str, float] | None = None
    try:
        time.sleep(REQUEST_SLEEP_SEC)
        _u, prior_entries, _ = load_month_shares(
            session, market, category, year - 1, month
        )
        prior_map = {b: s for b, s in prior_entries}
    except Exception as exc:  # noqa: BLE001
        print(
            f"  YoY skip ({market['code']}/{category['slug']}): {exc}",
            file=sys.stderr,
        )
        prior_map = None

    rankings = filter_rankings(entries, prior_map, category["chartKind"])
    if len(rankings) < MIN_RANKINGS:
        raise ValueError(
            f"Only {len(rankings)} rankings after filters "
            f"(need >= {MIN_RANKINGS}) for {market['name']} / {category['name']}"
        )

    source_url = source_page_url(market, category)
    slug = f"{market['pathPrefix']}/{category['slug']}"
    base: dict[str, Any] = {
        "slug": slug,
        "scope": market["scope"],
        "market": market["name"],
        "marketSlug": market["slug"],
        "marketCode": market["code"],
        "category": category["name"],
        "categorySlug": category["slug"],
        "period": period,
        "lastUpdated": date.today().isoformat(),
        "sourceName": "Statcounter Global Stats",
        "sourceUrl": source_url,
        "methodologyNote": category["methodology"],
        "rankings": rankings,
    }
    if market["scope"] == "country":
        base["country"] = market["name"]
        base["countryCode"] = market["code"]

    ai = openai_summaries(base)
    if ai:
        summary, faqs = ai
    else:
        summary, faqs = deterministic_summary_and_faqs(
            market["name"], category["name"], period, rankings, source_url
        )

    payload = {**base, "aiSummary": summary, "faqs": faqs}
    validate_payload(payload)
    return payload


def clear_stale_data(keep_paths: set[Path]) -> None:
    """Remove JSON files under src/data that were not rewritten this run."""
    if not DATA_DIR.exists():
        return
    for path in DATA_DIR.rglob("*.json"):
        if path.name.startswith("_"):
            path.unlink(missing_ok=True)
            continue
        if path.resolve() not in keep_paths:
            path.unlink(missing_ok=True)
    # Remove empty dirs (e.g. dropped markets like ghana)
    for path in sorted(DATA_DIR.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                path.rmdir()


def main() -> int:
    today = date.today()
    year, month = previous_complete_month(today)
    print(f"Target period: {month_label(year, month)} (today={today.isoformat()})")

    markets, categories = load_markets()
    print(f"Markets: {len(markets)}; categories: {len(categories)}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"})

    written: list[str] = []
    failures: list[str] = []
    keep: set[Path] = set()

    for market in markets:
        for category in categories:
            label = f"{market['name']} / {category['name']}"
            used_year, used_month = year, month
            try:
                time.sleep(REQUEST_SLEEP_SEC)
                try:
                    payload = scrape_one(session, market, category, used_year, used_month)
                except Exception as first_exc:
                    fy, fm = shift_month(used_year, used_month, -1)
                    print(
                        f"  {label}: {first_exc}; trying {month_label(fy, fm)}",
                        file=sys.stderr,
                    )
                    time.sleep(REQUEST_SLEEP_SEC)
                    payload = scrape_one(session, market, category, fy, fm)

                path = write_payload(market, category["slug"], payload)
                keep.add(path.resolve())
                top3 = ", ".join(
                    f"{r['brand']} {r['sharePercent']}%" for r in payload["rankings"][:3]
                )
                print(
                    f"OK  {label} [{payload['period']}]: {top3} -> {path.relative_to(ROOT)}"
                )
                written.append(str(path.relative_to(ROOT)))
            except Exception as exc:  # noqa: BLE001
                msg = f"FAIL {label}: {exc}"
                print(msg, file=sys.stderr)
                failures.append(msg)

    clear_stale_data(keep)

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "written": written,
        "failures": failures,
    }
    report_path = ROOT / "scripts" / "_scrape_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(written)} files; {len(failures)} failures. Report: {report_path}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
