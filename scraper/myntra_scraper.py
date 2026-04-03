"""
Myntra Lipstick Scraper
-----------------------
- Uses Selenium with headless Chrome + webdriver-manager
- Scrapes up to 5 pages of https://www.myntra.com/personal-care?f=Categories%3ALipstick
- Extracts: brand, name, prices, discount, rating, reviews, URL, image, breadcrumbs
- Exports to data/products.csv via scraper/export.py

Run: python -m scraper.myntra_scraper
"""
import logging
import random
import re
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from scraper.export import export_to_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.myntra.com/personal-care?f=Categories%3ALipstick"
MAX_PAGES = 5


def create_driver() -> webdriver.Chrome:
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
	driver = webdriver.Chrome(service=service, options=opts)
	driver.execute_script(
		"Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
	)
	return driver


def parse_card(card, page: int, pos: int) -> dict | None:
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
		"breadcrumbs": "Home/Personal Care/Lipstick",
		"category": "Lipstick",
		"sub_category": "Personal Care",
		"page_number": page,
		"position_on_page": pos,
	}


def scrape() -> list[dict]:
	all_products: list[dict] = []
	driver = create_driver()
	try:
		for page in range(1, MAX_PAGES + 1):
			url = BASE_URL if page == 1 else f"{BASE_URL}&p={page}"
			log.info(f"Scraping page {page}: {url}")
			driver.get(url)
			try:
				WebDriverWait(driver, 20).until(
					EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.product-base"))
				)
			except TimeoutException:
				log.warning(f"Timeout on page {page}, skipping.")
				continue

			for pct in [0.3, 0.6, 1.0]:
				driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pct});")
				time.sleep(0.6)

			cards = driver.find_elements(By.CSS_SELECTOR, "li.product-base")
			log.info(f"  Found {len(cards)} cards")
			for i, card in enumerate(cards, 1):
				product = parse_card(card, page, i)
				if product:
					all_products.append(product)

			time.sleep(random.uniform(2.5, 4.0))
	finally:
		driver.quit()

	log.info(f"Total scraped: {len(all_products)} products")
	if len(all_products) < 20:
		log.warning("Very few products scraped. Site may have blocked automation or changed markup.")
	export_to_csv(all_products)
	return all_products


if __name__ == "__main__":
	scrape()
