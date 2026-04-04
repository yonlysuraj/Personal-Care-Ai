"""
Myntra Dynamic Scraper
-----------------------
- Accepts ANY Myntra product listing URL + page count
- Uses Selenium with headless Chrome + webdriver-manager
- Extracts: brand, name, prices, discount, rating, reviews, URL, image, breadcrumbs
- Exports to category CSVs (for example data/products_lipstick.csv) via scraper/export.py

Usage:
  # Default (lipstick, 5 pages):
  python -m scraper.myntra_scraper

  # Custom URL + pages:
  python -m scraper.myntra_scraper "https://www.myntra.com/personal-care?f=Categories%3AEyeliner" 3

  # Or call from code:
  from scraper.myntra_scraper import scrape
  scrape(url="https://www.myntra.com/...", max_pages=3)
"""
import logging
import random
import re
import sys
import time
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs, urlparse

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config.logging_setup import get_logger
from scraper.export import export_to_csv

log = get_logger("scraper.myntra_scraper", app_name="ui")

DEFAULT_URL = "https://www.myntra.com/personal-care?f=Categories%3ALipstick"
DEFAULT_MAX_PAGES = 5


def category_to_slug(category: str) -> str:
	"""Convert category names like 'Nail Polish' to filename-safe slug 'nail_polish'."""
	slug = re.sub(r"[^a-zA-Z0-9]+", "_", category.strip().lower())
	return slug.strip("_") or "products"


def detect_category(url: str) -> tuple[str, str]:
	"""
	Extracts category info from a Myntra URL for breadcrumbs.
	Example: '...?f=Categories%3AEyeliner' -> ('Eyeliner', 'Home/Personal Care/Eyeliner')
	"""
	parsed = urlparse(url)
	params = parse_qs(parsed.query)

	category = "Personal Care"
	f_value = params.get("f", [""])[0]
	f_value = f_value.replace("%3A", ":")

	# Pattern: Categories:Lipstick / Categories:Nail Polish
	cat_match = re.search(r"Categories:([^,]+)", f_value, re.IGNORECASE)
	if cat_match:
		category = cat_match.group(1).strip()

	# Derive the path segment (e.g., /personal-care -> Personal Care)
	path_segment = parsed.path.strip("/").replace("-", " ").title() or "Personal Care"

	breadcrumbs = f"Home/{path_segment}/{category}"
	return category, breadcrumbs


def create_driver() -> Any:
	opts = Options()
	opts.add_argument("--headless=new")
	opts.add_argument("--no-sandbox")
	opts.add_argument("--disable-dev-shm-usage")
	opts.add_argument("--disable-blink-features=AutomationControlled")
	opts.add_experimental_option("excludeSwitches", ["enable-automation"])
	opts.add_argument(
		"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
	)
	service = Service(ChromeDriverManager().install())
	chrome_ctor = getattr(webdriver, "Chrome")
	driver = chrome_ctor(service=service, options=opts)
	driver.execute_script(
		"Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
	)
	return driver


def parse_card(card, page: int, pos: int, category: str, breadcrumbs: str) -> dict | None:
	def safe(selector: str, attr: str | None = None) -> str:
		try:
			el = card.find_element(By.CSS_SELECTOR, selector)
			return el.get_attribute(attr) if attr else el.text.strip()
		except NoSuchElementException:
			return "N/A"

	brand = safe(".product-brand")
	name = safe(".product-product")
	disc_price = safe(".product-discountedPrice")
	orig_price = safe(".product-strike") or disc_price
	disc_pct = safe(".product-discountPercentage")
	rating = safe(".product-ratingsContainer span")
	reviews_raw = safe(".product-ratingsCount")
	reviews = re.sub(r"[^\d]", "", reviews_raw) or "0"
	image_url = safe(".product-imageSliderContainer img", "src") or safe(
		".product-imageSliderContainer img", "data-src"
	)

	try:
		try:
			href = card.find_element(By.CSS_SELECTOR, "a.product-base").get_attribute("href")
		except NoSuchElementException:
			href = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
		product_url = href if href.startswith("http") else f"https://www.myntra.com{href}"
		pid_match = re.search(r"/(\d+)/buy", product_url)
		product_id = pid_match.group(1) if pid_match else f"p{page}{pos}"
	except NoSuchElementException:
		product_url, product_id = "N/A", f"p{page}{pos}"

	if brand == "N/A" and name == "N/A":
		return None

	return {
		"product_id": product_id,
		"brand": brand,
		"product_name": name,
		"discounted_price": disc_price,
		"original_price": orig_price,
		"discount_percentage": disc_pct,
		"rating": rating,
		"reviews_count": reviews,
		"image_url": image_url,
		"product_url": product_url,
		"breadcrumbs": breadcrumbs,
		"category": category,
		"sub_category": "Personal Care",
		"page_number": page,
		"position_on_page": pos,
	}


def scrape(
	url: str = DEFAULT_URL,
	max_pages: int = DEFAULT_MAX_PAGES,
	output_path: str | None = None,
) -> list[dict]:
	"""
	Scrape products from any Myntra listing URL.

	Args:
		url:       Full Myntra listing URL (e.g. 'https://www.myntra.com/personal-care?f=Categories%3AEyeliner')
		max_pages: Number of pages to scrape (1-10)
		output_path: Output CSV path. Defaults to category-specific file when None.
	"""
	max_pages = min(max(1, max_pages), 10)  # clamp 1-10
	category, breadcrumbs = detect_category(url)
	run_started = perf_counter()

	log.info("[STEP 1/6] Scrape request received")
	log.info("  Category: %s", category)
	log.info("  Breadcrumbs: %s", breadcrumbs)
	log.info("  Pages to scrape: %s", max_pages)
	log.info("  URL: %s", url)

	all_products: list[dict] = []
	log.info("[STEP 2/6] Initializing browser driver")
	driver = create_driver()
	log.info("[STEP 2/6] Browser driver ready")
	try:
		log.info("[STEP 3/6] Starting page-by-page scraping")
		for page in range(1, max_pages + 1):
			page_started = perf_counter()
			page_url = url if page == 1 else f"{url}&p={page}"
			log.info("  [PAGE %s/%s] Loading %s", page, max_pages, page_url)
			driver.get(page_url)
			try:
				WebDriverWait(driver, 20).until(
					EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.product-base"))
				)
			except TimeoutException:
				log.warning("  [PAGE %s/%s] Timeout waiting for product cards, skipping", page, max_pages)
				continue

			for pct in [0.3, 0.6, 1.0]:
				driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pct});")
				time.sleep(0.6)

			cards = driver.find_elements(By.CSS_SELECTOR, "li.product-base")
			log.info("  [PAGE %s/%s] Found %s cards", page, max_pages, len(cards))
			page_added = 0
			for i, card in enumerate(cards, 1):
				product = parse_card(card, page, i, category, breadcrumbs)
				if product:
					all_products.append(product)
					page_added += 1

			page_elapsed_ms = int((perf_counter() - page_started) * 1000)
			log.info(
				"  [PAGE %s/%s] Parsed=%s cumulative_total=%s elapsed_ms=%s",
				page,
				max_pages,
				page_added,
				len(all_products),
				page_elapsed_ms,
			)

			time.sleep(random.uniform(2.5, 4.0))
	finally:
		log.info("[STEP 4/6] Closing browser driver")
		driver.quit()

	log.info("[STEP 5/6] Scraping complete. Total products=%s", len(all_products))
	if len(all_products) < 20:
		log.warning("Very few products scraped. Site may have blocked automation or changed markup.")

	csv_path = output_path or f"data/products_{category_to_slug(category)}.csv"
	log.info("[STEP 6/6] Exporting to CSV path=%s", csv_path)
	export_to_csv(all_products, path=csv_path)
	run_elapsed_ms = int((perf_counter() - run_started) * 1000)
	log.info("[DONE] Scrape run finished in %s ms", run_elapsed_ms)
	return all_products


if __name__ == "__main__":
	# CLI: python -m scraper.myntra_scraper [URL] [MAX_PAGES]
	target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
	pages = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_PAGES
	log.info("Starting scraper from CLI with url=%s pages=%s", target_url, pages)

	scrape(url=target_url, max_pages=pages)
