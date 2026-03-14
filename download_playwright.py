#!/usr/bin/env python3
"""Download phone renders from GSMArena using Playwright.
Strategy: scrape full brand listing pages → build name→URL index → match each model → download image."""

import asyncio, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "https://www.gsmarena.com"
OUT  = Path("/home/billy/Desktop/serviceGSM/production")
SLEEP = 5  # seconds between requests

# brand_dir, gsmarena_slug, num_pages (approximate — we'll stop at last page), models
BRANDS = [
    {
        "dir": "xiaomiPics",
        "listing": "xiaomi-phones-80.php",
        "pagepat": "xiaomi-phones-f-80-0-p{}.php",
        "models": [
            ("mi-10",           "Mi 10"),
            ("mi-10-pro",       "Mi 10 Pro"),
            ("mi-10t",          "Mi 10T"),
            ("mi-10t-pro",      "Mi 10T Pro"),
            ("mi-10-lite",      "Mi 10 Lite"),
            ("mi-11",           "Mi 11"),
            ("mi-11-pro",       "Mi 11 Pro"),
            ("mi-11-ultra",     "Mi 11 Ultra"),
            ("mi-11-lite-5g",   "Mi 11 Lite 5G"),
            ("xiaomi-12",       "12"),
            ("xiaomi-12-pro",   "12 Pro"),
            ("xiaomi-12t",      "12T"),
            ("xiaomi-12t-pro",  "12T Pro"),
            ("xiaomi-12-lite",  "12 Lite"),
            ("xiaomi-13",       "13"),
            ("xiaomi-13-pro",   "13 Pro"),
            ("xiaomi-13t",      "13T"),
            ("xiaomi-13t-pro",  "13T Pro"),
            ("xiaomi-13-lite",  "13 Lite"),
            ("xiaomi-14",       "14"),
            ("xiaomi-14-pro",   "14 Pro"),
            ("xiaomi-14t",      "14T"),
            ("xiaomi-14t-pro",  "14T Pro"),
            ("xiaomi-15",       "15"),
            ("xiaomi-15-pro",   "15 Pro"),
        ],
    },
    {
        "dir": "huaweiPics",
        "listing": "huawei-phones-58.php",
        "pagepat": "huawei-phones-f-58-0-p{}.php",
        "models": [
            ("p30",           "P30"),
            ("p30-pro",       "P30 Pro"),
            ("nova-5t",       "nova 5T"),
            ("mate-30",       "Mate 30"),
            ("mate-30-pro",   "Mate 30 Pro"),
            ("p40",           "P40"),
            ("p40-lite",      "P40 Lite"),
            ("p40-pro",       "P40 Pro"),
            ("p40-pro-plus",  "P40 Pro+"),
            ("mate-40",       "Mate 40"),
            ("mate-40-pro",   "Mate 40 Pro"),
            ("p50",           "P50"),
            ("p50-pro",       "P50 Pro"),
            ("nova-9",        "nova 9"),
            ("nova-10",       "nova 10"),
            ("nova-10-pro",   "nova 10 Pro"),
            ("mate-50",       "Mate 50"),
            ("mate-50-pro",   "Mate 50 Pro"),
            ("pura-70",       "Pura 70"),
            ("pura-70-pro",   "Pura 70 Pro"),
            ("pura-70-ultra", "Pura 70 Ultra"),
        ],
    },
    {
        "dir": "honorPics",
        "listing": "honor-phones-121.php",
        "pagepat": "honor-phones-f-121-0-p{}.php",
        "models": [
            ("honor-90",          "90"),
            ("honor-90-pro",      "90 Pro"),
            ("honor-magic-5-pro", "Magic5 Pro"),
            ("honor-magic-6-pro", "Magic6 Pro"),
            ("honor-magic-7-pro", "Magic7 Pro"),
            ("honor-200",         "200"),
            ("honor-200-pro",     "200 Pro"),
            ("honor-x8b",         "X8b"),
            ("honor-x9b",         "X9b"),
            ("honor-x9c",         "X9c"),
        ],
    },
    {
        "dir": "oppoPics",
        "listing": "oppo-phones-82.php",
        "pagepat": "oppo-phones-f-82-0-p{}.php",
        "models": [
            ("reno-4",        "Reno4"),
            ("reno-4-pro",    "Reno4 Pro"),
            ("reno-5",        "Reno5"),
            ("reno-5-pro",    "Reno5 Pro"),
            ("reno-6",        "Reno6"),
            ("reno-6-pro",    "Reno6 Pro"),
            ("reno-7",        "Reno7"),
            ("reno-7-pro",    "Reno7 Pro"),
            ("reno-8",        "Reno8"),
            ("reno-8-pro",    "Reno8 Pro"),
            ("reno-10",       "Reno10"),
            ("reno-10-pro",   "Reno10 Pro"),
            ("reno-12",       "Reno12"),
            ("reno-12-pro",   "Reno12 Pro"),
            ("reno-13",       "Reno13"),
            ("reno-13-pro",   "Reno13 Pro"),
            ("find-x2",       "Find X2"),
            ("find-x2-pro",   "Find X2 Pro"),
            ("find-x3",       "Find X3"),
            ("find-x3-pro",   "Find X3 Pro"),
            ("find-x5",       "Find X5"),
            ("find-x5-pro",   "Find X5 Pro"),
            ("find-x6",       "Find X6"),
            ("find-x6-pro",   "Find X6 Pro"),
            ("find-x7",       "Find X7"),
            ("find-x7-ultra", "Find X7 Ultra"),
        ],
    },
    {
        "dir": "motorolaPics",
        "listing": "motorola-phones-4.php",
        "pagepat": "motorola-phones-f-4-0-p{}.php",
        "models": [
            ("moto-g9-play",        "moto g9 play"),
            ("moto-g9-plus",        "moto g9 plus"),
            ("moto-g9-power",       "moto g9 power"),
            ("moto-g30",            "moto g30"),
            ("moto-g50",            "moto g50"),
            ("moto-g60",            "moto g60"),
            ("moto-g72",            "moto g72"),
            ("moto-g82-5g",         "moto g82 5G"),
            ("moto-g14",            "moto g14"),
            ("moto-g24",            "moto g24"),
            ("moto-g34-5g",         "moto g34 5G"),
            ("moto-g44-5g",         "moto g44 5G"),
            ("moto-g54-5g",         "moto g54 5G"),
            ("moto-g64-5g",         "moto g64 5G"),
            ("moto-g84-5g",         "moto g84 5G"),
            ("moto-g85-5g",         "moto g85 5G"),
            ("moto-edge-20",        "edge 20"),
            ("moto-edge-20-pro",    "edge 20 pro"),
            ("moto-edge-30",        "edge 30"),
            ("moto-edge-30-pro",    "edge 30 pro"),
            ("moto-edge-30-neo",    "edge 30 neo"),
            ("moto-edge-30-ultra",  "edge 30 ultra"),
            ("moto-edge-40",        "edge 40"),
            ("moto-edge-40-pro",    "edge 40 pro"),
            ("moto-edge-40-neo",    "edge 40 neo"),
            ("moto-edge-50",        "edge 50"),
            ("moto-edge-50-pro",    "edge 50 pro"),
            ("moto-edge-50-ultra",  "edge 50 ultra"),
            ("moto-edge-50-fusion", "edge 50 fusion"),
        ],
    },
    {
        "dir": "oneplusPics",
        "listing": "oneplus-phones-95.php",
        "pagepat": "oneplus-phones-f-95-0-p{}.php",
        "models": [
            ("oneplus-8",      "8"),
            ("oneplus-8-pro",  "8 Pro"),
            ("oneplus-8t",     "8T"),
            ("oneplus-9",      "9"),
            ("oneplus-9-pro",  "9 Pro"),
            ("oneplus-9r",     "9R"),
            ("oneplus-10-pro", "10 Pro"),
            ("oneplus-10t",    "10T"),
            ("oneplus-11",     "11"),
            ("oneplus-11r",    "11R"),
            ("oneplus-12",     "12"),
            ("oneplus-12r",    "12R"),
            ("oneplus-13",     "13"),
            ("oneplus-13r",    "13R"),
            ("nord",           "Nord"),
            ("nord-2",         "Nord 2"),
            ("nord-2t",        "Nord 2T"),
            ("nord-3",         "Nord 3"),
            ("nord-4",         "Nord 4"),
            ("nord-ce",        "Nord CE"),
            ("nord-ce-2",      "Nord CE 2"),
            ("nord-ce-3",      "Nord CE 3"),
            ("nord-ce-4",      "Nord CE 4"),
        ],
    },
    {
        "dir": "realmePics",
        "listing": "realme-phones-118.php",
        "pagepat": "realme-phones-f-118-0-p{}.php",
        "models": [
            ("realme-8",           "8"),
            ("realme-8-pro",       "8 Pro"),
            ("realme-8i",          "8i"),
            ("realme-9",           "9"),
            ("realme-9-pro",       "9 Pro"),
            ("realme-9-pro-plus",  "9 Pro+"),
            ("realme-9i",          "9i"),
            ("realme-10",          "10"),
            ("realme-10-pro",      "10 Pro"),
            ("realme-10-pro-plus", "10 Pro+"),
            ("realme-11",          "11"),
            ("realme-11-pro",      "11 Pro"),
            ("realme-11-pro-plus", "11 Pro+"),
            ("realme-12",          "12"),
            ("realme-12-pro",      "12 Pro"),
            ("realme-12-pro-plus", "12 Pro+"),
            ("realme-gt",          "GT"),
            ("realme-gt-2",        "GT 2"),
            ("realme-gt-2-pro",    "GT 2 Pro"),
            ("realme-gt-neo-2",    "GT Neo2"),
            ("realme-gt-neo-3",    "GT Neo3"),
            ("realme-gt-neo-5",    "GT Neo5"),
            ("realme-gt-6",        "GT 6"),
            ("realme-c31",         "C31"),
            ("realme-c33",         "C33"),
            ("realme-c35",         "C35"),
            ("realme-c51",         "C51"),
            ("realme-c53",         "C53"),
            ("realme-c55",         "C55"),
            ("realme-c67",         "C67"),
        ],
    },
    {
        "dir": "googlePics",
        "listing": "google-phones-107.php",
        "pagepat": "google-phones-f-107-0-p{}.php",
        "models": [
            ("pixel-6",          "Pixel 6"),
            ("pixel-6-pro",      "Pixel 6 Pro"),
            ("pixel-6a",         "Pixel 6a"),
            ("pixel-7",          "Pixel 7"),
            ("pixel-7-pro",      "Pixel 7 Pro"),
            ("pixel-7a",         "Pixel 7a"),
            ("pixel-8",          "Pixel 8"),
            ("pixel-8-pro",      "Pixel 8 Pro"),
            ("pixel-8a",         "Pixel 8a"),
            ("pixel-9",          "Pixel 9"),
            ("pixel-9-pro",      "Pixel 9 Pro"),
            ("pixel-9-pro-xl",   "Pixel 9 Pro XL"),
            ("pixel-9-pro-fold", "Pixel 9 Pro Fold"),
            ("pixel-fold",       "Pixel Fold"),
        ],
    },
]

failed = []
ok_count = 0


async def build_index(page, brand):
    """Scrape all listing pages for a brand, return {name_lower: href}."""
    index = {}
    url = f"{BASE}/{brand['listing']}"
    pagepat = brand["pagepat"]
    page_num = 1

    while True:
        print(f"  Indexing page {page_num}...")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(SLEEP)

        if "Too Many Requests" in await page.title():
            print("  RATE LIMITED during indexing!")
            break

        items = await page.query_selector_all("div.makers ul li a")
        if not items:
            break
        for item in items:
            span = await item.query_selector("span")
            name = (await span.inner_text()).strip() if span else (await item.inner_text()).strip()
            href = await item.get_attribute("href")
            if name and href:
                index[name.lower()] = href

        # Check if there's a next page
        next_link = await page.query_selector(f'a[href="{pagepat.format(page_num + 1)}"]')
        if not next_link:
            break
        page_num += 1
        url = f"{BASE}/{pagepat.format(page_num)}"

    print(f"  Index built: {len(index)} devices")
    return index


def best_match(index, query):
    """Find best matching href for a model name in the index."""
    q = query.lower().strip()

    # Exact match
    if q in index:
        return index[q]

    # Substring match — find entries where query appears in name or vice versa
    candidates = []
    for name, href in index.items():
        if q == name:
            return href
        # Score by word overlap penalising extra words
        q_words = set(q.split())
        n_words = set(name.split())
        matched = len(q_words & n_words)
        extra = len(n_words - q_words)
        if matched == len(q_words):  # all query words found
            candidates.append((matched - extra * 0.5, name, href))

    if candidates:
        candidates.sort(reverse=True)
        print(f"    Matched '{query}' → '{candidates[0][1]}'")
        return candidates[0][2]

    return None


async def main():
    global ok_count

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # Warm up with homepage
        await page.goto(BASE, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        for brand in BRANDS:
            print(f"\n=== {brand['dir']} ===")

            # Build full index for this brand
            index = await build_index(page, brand)

            for slug, model_name in brand["models"]:
                out_path = OUT / brand["dir"] / f"{slug}.jpg"
                if out_path.exists():
                    print(f"  SKIP {slug}")
                    continue

                href = best_match(index, model_name)
                if not href:
                    print(f"  FAIL (not in index) {model_name}")
                    failed.append(f"{brand['dir']}/{model_name}")
                    continue

                # Fetch device page
                await page.goto(f"{BASE}/{href}", wait_until="domcontentloaded")
                await asyncio.sleep(SLEEP)

                if "Too Many Requests" in await page.title():
                    print("  RATE LIMITED — stopping")
                    break

                img_el = await page.query_selector("div.specs-photo-main img")
                img_url = await img_el.get_attribute("src") if img_el else None
                if not img_url:
                    print(f"  FAIL (no image) {model_name}")
                    failed.append(f"{brand['dir']}/{model_name}")
                    continue

                resp = await ctx.request.get(img_url)
                if resp.ok:
                    out_path.write_bytes(await resp.body())
                    print(f"  OK  {slug}")
                    ok_count += 1
                else:
                    print(f"  FAIL (download {resp.status}) {model_name}")
                    failed.append(f"{brand['dir']}/{model_name}")

                await asyncio.sleep(SLEEP)

        await browser.close()

    print(f"\n=== DONE === OK:{ok_count} FAILED:{len(failed)}")
    for f in failed:
        print(f"  - {f}")


asyncio.run(main())
