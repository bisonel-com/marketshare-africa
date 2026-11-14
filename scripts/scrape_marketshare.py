#!/usr/bin/env python3
"""
Fetch market-share rankings from Statcounter, Stack Overflow Survey, RDW and DfT.

Markets: src/config/markets.json
Categories: src/config/categories.json
Never invents figures. Geos with fewer than 3 rankings are written with hasData=false.
Publish month for Statcounter: October 2026 (202610) only.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import urllib.parse
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "data"
MARKETS_PATH = ROOT / "src" / "config" / "markets.json"
CATEGORIES_PATH = ROOT / "src" / "config" / "categories.json"

USER_AGENT = "GlobalMarketShareBot/1.0 (+https://xmarketshare.com; research)"
REQUEST_SLEEP_SEC = 1.0
MIN_SHARE = 0.1
MAX_RANKINGS = 10
MIN_RANKINGS = 3
STATCOUNTER_PERIOD = (2026, 10)  # October 2026 only

DROP_BRANDS = {"other", "unknown", "[unknown]", "n/a", "na", "none"}

DATA_SCHEMA: dict[str, Any] = {
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
        "hasData",
        "metricLabel",
        "licenceName",
        "licenceUrl",
    ],
    "properties": {
        "slug": {"type": "string"},
        "scope": {"type": "string"},
        "market": {"type": "string"},
        "marketSlug": {"type": "string"},
        "marketCode": {"type": "string"},
        "category": {"type": "string"},
        "categorySlug": {"type": "string"},
        "period": {"type": "string"},
        "lastUpdated": {"type": "string"},
        "sourceName": {"type": "string"},
        "sourceUrl": {"type": "string"},
        "methodologyNote": {"type": "string"},
        "aiSummary": {"type": "string"},
        "faqs": {"type": "array"},
        "rankings": {"type": "array"},
        "hasData": {"type": "boolean"},
        "metricLabel": {"type": "string"},
        "licenceName": {"type": "string"},
        "licenceUrl": {"type": "string"},
        "derivedLicenceName": {"type": "string"},
        "derivedLicenceUrl": {"type": "string"},
        "attributionNote": {"type": "string"},
        "family": {"type": "string"},
        "device": {"type": "string"},
        "country": {"type": "string"},
        "countryCode": {"type": "string"},
        "source": {"type": "string"},
    },
    "additionalProperties": True,
}


def load_config() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    markets_raw = json.loads(MARKETS_PATH.read_text(encoding="utf-8"))
    cats_raw = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    markets = [markets_raw["worldwide"], *markets_raw["regions"], *markets_raw["countries"]]
    return markets, cats_raw["categories"]


def month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%B %Y")


def build_csv_url(market: dict[str, Any], category: dict[str, Any], year: int, month: int) -> str:
    yyyymm = f"{year}{month:02d}"
    yyyy_mm = f"{year}-{month:02d}"
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
    base = f"https://gs.statcounter.com/{category['sourcePath']}".rstrip("/")
    if market["scope"] == "worldwide":
        return base
    return f"{base}/{market['slug']}"


def fetch_text(session: requests.Session, url: str) -> str:
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


def parse_share_csv(text: str) -> list[tuple[str, float]]:
    reader = csv.reader(io.StringIO(text.strip()))
    rows = list(reader)
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
    return entries


def filter_rankings(entries: list[tuple[str, float]]) -> list[dict[str, Any]]:
    cleaned = [
        (b, s)
        for b, s in entries
        if b.strip().lower() not in DROP_BRANDS and s > MIN_SHARE
    ]
    cleaned.sort(key=lambda x: (-x[1], x[0].lower()))
    cleaned = cleaned[:MAX_RANKINGS]
    out = []
    for i, (brand, share) in enumerate(cleaned, start=1):
        out.append(
            {
                "rank": i,
                "brand": brand,
                "parentCompany": "Independent / Listed",
                "sharePercent": round(share, 2),
                "yoyChange": None,
                "segment": "Consumer Market",
                "highlight": i == 1,
            }
        )
    return out


def deterministic_copy(
    market: str,
    category: str,
    period: str,
    rankings: list[dict[str, Any]],
    metric_label: str,
    source_url: str,
    has_data: bool,
) -> tuple[str, list[dict[str, str]]]:
    if not has_data:
        summary = (
            f"No ranking is published for {category} in {market} for {period}: "
            f"fewer than {MIN_RANKINGS} brands met the minimum share threshold in the source data."
        )
        faqs = [
            {
                "question": f"Why is there no ranking for {category} in {market}?",
                "answer": (
                    f"The source returned fewer than {MIN_RANKINGS} brands above {MIN_SHARE}% "
                    f"after filters. Global Market Share does not invent figures."
                ),
            },
            {
                "question": "Where does the data come from?",
                "answer": f"Source page: {source_url}.",
            },
        ]
        return summary, faqs

    top = rankings[0]
    second = rankings[1] if len(rankings) > 1 else None
    third = rankings[2] if len(rankings) > 2 else None
    parts = [
        f"In {period}, {top['brand']} led {category.lower()} in {market} at "
        f"{top['sharePercent']}% ({metric_label})."
    ]
    if second and third:
        parts.append(
            f"{second['brand']} ranked second at {second['sharePercent']}%, "
            f"followed by {third['brand']} at {third['sharePercent']}%."
        )
    summary = " ".join(parts)
    faqs = [
        {
            "question": f"Which item leads {category.lower()} in {market}?",
            "answer": (
                f"{top['brand']} leads at {top['sharePercent']}% in {period} "
                f"({metric_label}). Source: {source_url}."
            ),
        },
        {
            "question": f"What does the {metric_label} metric mean?",
            "answer": (
                f"Figures are {metric_label} from the cited source for {period}. "
                "They are not invented estimates."
            ),
        },
        {
            "question": f"What are the top three for {category.lower()} in {market}?",
            "answer": ", ".join(
                f"{r['brand']} ({r['sharePercent']}%)" for r in rankings[:3]
            )
            + f" in {period}.",
        },
    ]
    return summary, faqs


def write_payload(market: dict[str, Any], category_slug: str, payload: dict[str, Any]) -> Path:
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


def build_payload(
    market: dict[str, Any],
    category: dict[str, Any],
    rankings: list[dict[str, Any]],
    period: str,
    source_url: str,
    attribution_note: str = "",
) -> dict[str, Any]:
    has_data = len(rankings) >= MIN_RANKINGS
    if not has_data:
        rankings = []
    summary, faqs = deterministic_copy(
        market["name"],
        category["name"],
        period,
        rankings,
        category["metricLabel"],
        source_url,
        has_data,
    )
    payload: dict[str, Any] = {
        "slug": f"{market['pathPrefix']}/{category['slug']}",
        "scope": market["scope"],
        "market": market["name"],
        "marketSlug": market["slug"],
        "marketCode": market["code"],
        "category": category["name"],
        "categorySlug": category["slug"],
        "family": category.get("family", ""),
        "device": category.get("device", ""),
        "period": period,
        "lastUpdated": date.today().isoformat(),
        "sourceName": category["sourceName"],
        "sourceUrl": source_url,
        "source": category["source"],
        "methodologyNote": category["methodology"],
        "metricLabel": category["metricLabel"],
        "licenceName": category["licenceName"],
        "licenceUrl": category["licenceUrl"],
        "derivedLicenceName": category.get("derivedLicenceName", ""),
        "derivedLicenceUrl": category.get("derivedLicenceUrl", ""),
        "attributionNote": attribution_note,
        "aiSummary": summary,
        "faqs": faqs,
        "rankings": rankings,
        "hasData": has_data,
    }
    if market["scope"] == "country":
        payload["country"] = market["name"]
        payload["countryCode"] = market["code"]
    Draft202012Validator(DATA_SCHEMA).validate(payload)
    return payload


def geos_for_category(markets: list[dict[str, Any]], category: dict[str, Any]) -> list[dict[str, Any]]:
    cov = category.get("geoCoverage", "full")
    if cov == "worldwide-only":
        return [m for m in markets if m["scope"] == "worldwide"]
    if cov == "single-country":
        slug = category.get("geoSlug")
        return [m for m in markets if m["slug"] == slug]
    return markets


def scrape_statcounter(
    session: requests.Session,
    markets: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    year, month = STATCOUNTER_PERIOD
    period = month_label(year, month)
    written: list[str] = []
    failures: list[str] = []
    cats = [c for c in categories if c["source"] == "statcounter"]
    for category in cats:
        for market in geos_for_category(markets, category):
            label = f"{market['name']} / {category['name']}"
            try:
                time.sleep(REQUEST_SLEEP_SEC)
                url = build_csv_url(market, category, year, month)
                text = fetch_text(session, url)
                if not text.strip() or "<html" in text[:200].lower():
                    raise ValueError("non-CSV response")
                entries = parse_share_csv(text)
                rankings = filter_rankings(entries)
                payload = build_payload(
                    market,
                    category,
                    rankings,
                    period,
                    source_page_url(market, category),
                )
                path = write_payload(market, category["slug"], payload)
                written.append(str(path.relative_to(ROOT)))
                status = "OK" if payload["hasData"] else "EMPTY"
                top = ", ".join(
                    f"{r['brand']} {r['sharePercent']}%" for r in payload["rankings"][:3]
                )
                print(f"{status} {label}: {top or 'no data'} -> {path.relative_to(ROOT)}")
            except Exception as exc:  # noqa: BLE001
                msg = f"FAIL {label}: {exc}"
                print(msg, file=sys.stderr)
                failures.append(msg)
    return written, failures


def scrape_stackoverflow(
    session: requests.Session,
    markets: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    written: list[str] = []
    failures: list[str] = []
    cats = [c for c in categories if c["source"] == "stackoverflow"]
    if not cats:
        return written, failures
    url = cats[0]["sourceDataUrl"]
    print(f"Downloading Stack Overflow survey CSV from {url}")
    try:
        time.sleep(REQUEST_SLEEP_SEC)
        resp = session.get(url, timeout=180)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(resp.content), low_memory=False)
    except Exception as exc:  # noqa: BLE001
        return written, [f"FAIL Stack Overflow download: {exc}"]

    worldwide = next(m for m in markets if m["scope"] == "worldwide")
    n = len(df)
    note = (
        "Derived from Stack Overflow Developer Survey 2025 (ODbL 1.0 / DbCL 1.0). "
        "Share-alike applies to the derived database."
    )
    for category in cats:
        col = category["soColumn"]
        try:
            if col not in df.columns:
                raise KeyError(f"missing column {col}")
            counter: Counter[str] = Counter()
            series = df[col].dropna()
            for row in series:
                for part in str(row).split(";"):
                    p = part.strip()
                    if p and p.lower() not in DROP_BRANDS:
                        counter[p] += 1
            entries = [(k, v / n * 100.0) for k, v in counter.items()]
            rankings = filter_rankings(entries)
            # For survey %, keep values even if below 0.1 after already filtered
            payload = build_payload(
                worldwide,
                category,
                rankings,
                category["period"],
                category["sourceHomeUrl"],
                attribution_note=note,
            )
            path = write_payload(worldwide, category["slug"], payload)
            written.append(str(path.relative_to(ROOT)))
            top = ", ".join(
                f"{r['brand']} {r['sharePercent']}%" for r in payload["rankings"][:3]
            )
            print(f"OK Worldwide / {category['name']}: {top}")
        except Exception as exc:  # noqa: BLE001
            msg = f"FAIL Worldwide / {category['name']}: {exc}"
            print(msg, file=sys.stderr)
            failures.append(msg)
    return written, failures


def scrape_rdw(
    session: requests.Session,
    markets: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    written: list[str] = []
    failures: list[str] = []
    cats = [c for c in categories if c["source"] == "rdw"]
    if not cats:
        return written, failures
    market = next(m for m in markets if m["slug"] == "netherlands")
    # Socrata aggregation; page through if needed using $limit
    url = (
        "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
        "?$select=merk,count(*)%20as%20cnt&$group=merk&$order=cnt%20DESC&$limit=50000"
    )
    try:
        time.sleep(REQUEST_SLEEP_SEC)
        rows = session.get(url, timeout=120).json()
        entries = []
        total = sum(int(r["cnt"]) for r in rows)
        for r in rows:
            brand = str(r["merk"]).strip().title()
            share = int(r["cnt"]) / total * 100.0
            entries.append((brand, share))
        category = cats[0]
        rankings = filter_rankings(entries)
        payload = build_payload(
            market,
            category,
            rankings,
            f"RDW extract {date.today().isoformat()}",
            category["sourceHomeUrl"],
            attribution_note="Credit: RDW (Netherlands vehicle authority) open data.",
        )
        # Override period to something readable
        payload["period"] = date.today().strftime("%B %Y") + " extract"
        path = write_payload(market, category["slug"], payload)
        written.append(str(path.relative_to(ROOT)))
        top = ", ".join(f"{r['brand']} {r['sharePercent']}%" for r in payload["rankings"][:3])
        print(f"OK Netherlands / {category['name']}: {top}")
    except Exception as exc:  # noqa: BLE001
        msg = f"FAIL RDW: {exc}"
        print(msg, file=sys.stderr)
        failures.append(msg)
    return written, failures


def scrape_dft(
    session: requests.Session,
    markets: list[dict[str, Any]],
    categories: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    written: list[str] = []
    failures: list[str] = []
    cats = [c for c in categories if c["source"] == "dft"]
    if not cats:
        return written, failures
    category = cats[0]
    market = next(m for m in markets if m["slug"] == "united-kingdom")
    try:
        time.sleep(REQUEST_SLEEP_SEC)
        text = fetch_text(session, category["sourceDataUrl"])
        df = pd.read_csv(io.StringIO(text))
        # Latest quarter column after LicenceStatus
        period_cols = [c for c in df.columns if c not in {
            "BodyType", "Make", "GenModel", "Model", "Fuel", "LicenceStatus"
        }]
        latest = period_cols[0]
        cars = df[(df["BodyType"] == "Cars") & (df["LicenceStatus"] == "Licensed")]
        grouped = cars.groupby("Make", as_index=False)[latest].sum()
        total = float(grouped[latest].sum())
        entries = [
            (str(r["Make"]).title(), float(r[latest]) / total * 100.0)
            for _, r in grouped.iterrows()
        ]
        rankings = filter_rankings(entries)
        note = (
            "Contains public sector information licensed under the Open Government Licence v3.0."
        )
        payload = build_payload(
            market,
            {**category, "period": latest},
            rankings,
            latest,
            category["sourceHomeUrl"],
            attribution_note=note,
        )
        path = write_payload(market, category["slug"], payload)
        written.append(str(path.relative_to(ROOT)))
        top = ", ".join(f"{r['brand']} {r['sharePercent']}%" for r in payload["rankings"][:3])
        print(f"OK United Kingdom / {category['name']} [{latest}]: {top}")
    except Exception as exc:  # noqa: BLE001
        msg = f"FAIL DfT: {exc}"
        print(msg, file=sys.stderr)
        failures.append(msg)
    return written, failures


def clear_stale(keep: set[Path]) -> None:
    if not DATA_DIR.exists():
        return
    for path in DATA_DIR.rglob("*.json"):
        if path.resolve() not in keep:
            path.unlink(missing_ok=True)
    for path in sorted(DATA_DIR.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                path.rmdir()


def main() -> int:
    markets, categories = load_config()
    print(f"Markets={len(markets)} categories={len(categories)}")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    written: list[str] = []
    failures: list[str] = []

    for fn in (scrape_statcounter, scrape_stackoverflow, scrape_rdw, scrape_dft):
        w, f = fn(session, markets, categories)
        written.extend(w)
        failures.extend(f)

    keep = {(ROOT / p).resolve() for p in written}
    clear_stale(keep)

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "written": written,
        "failures": failures,
        "counts": {
            "written": len(written),
            "failures": len(failures),
            "categories": len(categories),
            "markets": len(markets),
        },
    }
    report_path = ROOT / "scripts" / "_scrape_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(written)} files; {len(failures)} failures. Report: {report_path}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
