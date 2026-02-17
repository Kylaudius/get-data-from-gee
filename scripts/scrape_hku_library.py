#!/usr/bin/env python3
"""Scrape HKU Library Primo search results for a given keyword.

Example:
  python scripts/scrape_hku_library.py --query "上海 风貌 别墅" --pages 3 --output data/hku_shanghai_villa.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import quote

BASE_URL = "https://find.lib.hku.hk/discovery/search"


def build_url(query: str, offset: int) -> str:
    q = quote(query)
    return (
        f"{BASE_URL}?query=any,contains,{q}"
        "&tab=Everything&search_scope=Everything"
        "&vid=852UHK_INST:HKU&lang=zh-cn"
        f"&offset={offset}"
    )


def scrape(query: str, pages: int, headless: bool = True) -> list[dict[str, str]]:
    from playwright.sync_api import sync_playwright

    rows: list[dict[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for page_idx in range(pages):
            offset = page_idx * 10
            url = build_url(query, offset)
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_selector("prm-brief-result-container", timeout=120_000)
            page.wait_for_timeout(2500)

            items = page.evaluate(
                r"""
                () => {
                  const cards = Array.from(document.querySelectorAll('prm-brief-result-container')); 
                  return cards.map((card) => {
                    const titleEl = card.querySelector('h3.item-title, h2.item-title, a[data-qa="title"]');
                    const title = titleEl ? titleEl.textContent.trim().replace(/\s+/g, ' ') : '';

                    const creators = Array.from(card.querySelectorAll('.item-details prm-authors span, .item-details .item-detail')).map(n => n.textContent.trim()).join(' | ');

                    const dateEl = card.querySelector('.item-details .display-date, .item-details [class*="date"]');
                    const year = dateEl ? dateEl.textContent.trim() : '';

                    const typeEl = card.querySelector('.media-type, .item-type');
                    const material_type = typeEl ? typeEl.textContent.trim() : '';

                    const linkEl = card.querySelector('a[href*="fulldisplay"]');
                    const link = linkEl ? linkEl.href : '';

                    return { title, creators, year, material_type, link };
                  });
                }
                """
            )

            for item in items:
                if item.get("title"):
                    item["query"] = query
                    item["offset"] = str(offset)
                    rows.append(item)

            time.sleep(1)

        browser.close()

    return rows


def write_output(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    fieldnames = ["query", "title", "creators", "year", "material_type", "link", "offset"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape HKU Library search results.")
    parser.add_argument("--query", required=True, help="Search keyword, e.g. '上海 风貌 别墅'")
    parser.add_argument("--pages", type=int, default=2, help="How many result pages to scrape (10 items/page).")
    parser.add_argument("--output", default="data/hku_results.csv", help="Output path (.csv or .json).")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode for debugging.")
    args = parser.parse_args()

    rows = scrape(args.query, pages=args.pages, headless=not args.headed)
    write_output(Path(args.output), rows)
    print(f"Saved {len(rows)} records to {args.output}")


if __name__ == "__main__":
    main()
