#Jumia Egypt Product Scraper
#we're scraping product data from jumia.com.eg for finding market insights 

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import random
import os
from datetime import datetime


CATEGORIES = [
    ("televisions", 5),
    ("mobile-phones", 5),
    ("air-fryers", 3),
    ("blenders", 3),
    ("laptops", 4),
    ("refrigerators", 3),
    ("kids-fashion", 3),
    ("mens-sneakers", 3),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
}


def sleep():
    time.sleep(random.uniform(0.35, 0.9))


def fetch(session, url):
    # here we make a GET request to the given URL
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            return resp.text
        elif resp.status_code == 429:
            print(f"Rate limited, sleeping 60s...")
            time.sleep(60)
        else:
            print(f"Got {resp.status_code} for {url}")
    except Exception as e:
        print(f"Error: {e}")
    return None


def get_product_urls(html):
    # here we parse the listing page and extract product URLs
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("article.prd a.core"):
        href = a.get("href", "")
        if href:
            urls.append("https://www.jumia.com.eg" + href)
    return list(set(urls))


def parse_product(html, url, category):
    # here we parse the product detail page and extract the required fields
    soup = BeautifulSoup(html, "html.parser")

    store = None
    for script in soup.find_all("script"):
        if script.string and "window.__STORE__" in script.string:
            try:
                raw = script.string.split("window.__STORE__=", 1)[1].strip().rstrip(";")
                store = json.loads(raw)
            except:
                pass
            break

    if not store or not store.get("products"):
        return None

    p = store["products"][0]
    prices = p.get("prices", {})
    rating = p.get("rating", {})
    now = datetime.now()

    def to_float(val):
        if not val:
            return None
        try:
            return float(str(val).replace(",", "").replace(" جنيه", "").strip())
        except:
            return None

    return {
        "date":          now.strftime("%Y-%m-%d"),
        "time":          now.strftime("%H:%M:%S"),
        "sku":           p.get("sku", ""),
        "name":          p.get("name", ""),
        "brand":         p.get("brand", ""),
        "category":      category,
        "category_path": " > ".join(p.get("categories", [])),
        "price":         to_float(prices.get("rawPrice")),
        "old_price":     to_float(prices.get("oldPrice")),
        "discount_pct": str(prices.get("discount", "")).replace("%", ""),
        "rating":        rating.get("average"),
        "reviews":       rating.get("totalRatings"),
        "in_stock":      p.get("isBuyable", False),
        "express":       p.get("isShopExpress", False),
        "url":           url,
    }


def save(rows, path):
    if not rows:
        return
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows → {path}")


def main():
    session = requests.Session()
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs("data", exist_ok=True)
    output = f"data/jumia_{today}.csv"

    for category, max_pages in CATEGORIES:
        print(f"\n── {category} ──")
        product_urls = []

        for page in range(1, max_pages + 1):
            url = f"https://www.jumia.com.eg/{category}/?page={page}"
            print(f"  Listing page {page}...")
            html = fetch(session, url)
            if not html:
                break
            urls = get_product_urls(html)
            if not urls:
                break
            product_urls.extend(urls)
            sleep()

        batch = []
        for i, url in enumerate(product_urls, 1):
            print(f"  Product {i}/{len(product_urls)}")
            html = fetch(session, url)
            if html:
                product = parse_product(html, url, category)
                if product:
                    batch.append(product)
            sleep()

            if len(batch) >= 20:
                save(batch, output)
                batch = []

        save(batch, output)

    print(f"\nDone. Output: {output}")


if __name__ == "__main__":
    main()
