"""
Streamlit Chat UI.

Calls the FastAPI backend via HTTP.
Session ID is stored in session_state so each browser tab has one conversation.
"""

import os
from pathlib import Path
import sys
import uuid

import httpx
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

from config.logging_setup import get_logger

API_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
logger = get_logger("ui.streamlit_app", app_name="ui")
CHAT_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=90.0, write=30.0, pool=90.0)
RELOAD_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=20.0, pool=60.0)

st.set_page_config(
	page_title="Myra - Beauty Assistant",
	page_icon=":lipstick:",
	layout="centered",
)


if "session_id" not in st.session_state:
	st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
	st.session_state.messages = []

logger.info("Streamlit session initialized with session_id=%s", st.session_state.session_id)


st.markdown("## Myra - Personal Care Assistant")
st.caption("Powered by Groq, Llama 3.3 70B, PostgreSQL")
st.divider()


for msg in st.session_state.messages:
	with st.chat_message(msg["role"]):
		st.markdown(msg["content"])
		if msg.get("is_handoff"):
			st.warning("Escalated to human support team.")


if not st.session_state.messages:
	with st.chat_message("assistant"):
		st.markdown(
			"Hi! I am Myra, your personal care assistant.\n\n"
			"I can help you find lipstick products, answer beauty questions, "
			"and recommend shades for your skin tone."
		)


if prompt := st.chat_input("Ask about products or beauty tips..."):
	logger.info("User message received in session_id=%s", st.session_state.session_id)
	with st.chat_message("user"):
		st.markdown(prompt)
	st.session_state.messages.append({"role": "user", "content": prompt})

	with st.chat_message("assistant"):
		with st.spinner("Thinking..."):
			try:
				resp = httpx.post(
					f"{API_URL}/api/chat",
					json={
						"message": prompt,
						"session_id": st.session_state.session_id,
					},
					timeout=CHAT_HTTP_TIMEOUT,
				)
				resp.raise_for_status()
				data = resp.json()
				reply = data["reply"]
				is_handoff = data["is_handoff"]
			except httpx.ReadTimeout as exc:
				logger.exception("Backend chat call timed out for session_id=%s", st.session_state.session_id)
				reply = (
					"The request is taking longer than expected while processing the current dataset. "
					"Please try again in a few seconds."
				)
				is_handoff = False
			except httpx.HTTPError as exc:
				logger.exception("Backend call failed for session_id=%s", st.session_state.session_id)
				reply = f"Sorry, I am having trouble connecting. Please try again. ({exc})"
				is_handoff = False

		st.markdown(reply)
		if is_handoff:
			st.warning("Escalated to human support team.")

	st.session_state.messages.append(
		{
			"role": "assistant",
			"content": reply,
			"is_handoff": is_handoff,
		}
	)
	logger.info("Assistant message stored in session_id=%s", st.session_state.session_id)


with st.sidebar:
	st.markdown("### Scrape Myntra")
	scrape_url = st.text_input(
		"Listing URL",
		value="https://www.myntra.com/personal-care?f=Categories%3ALipstick",
	)
	page_count = st.slider("Pages", min_value=1, max_value=10, value=3)

	if st.button("Scrape Products"):
		with st.spinner("Scraping products. This can take 1-3 minutes..."):
			try:
				from scraper.myntra_scraper import category_to_slug, detect_category, scrape

				category, _ = detect_category(scrape_url)
				csv_path = ROOT_DIR / "data" / f"products_{category_to_slug(category)}.csv"
				scraped = scrape(url=scrape_url, max_pages=page_count, output_path=str(csv_path))
				reload_resp = httpx.post(
					f"{API_URL}/api/products/reload",
					params={"csv_path": str(csv_path)},
					timeout=RELOAD_HTTP_TIMEOUT,
				)
				reload_resp.raise_for_status()
				reload_data = reload_resp.json()
				st.success(
					f"Scraped {len(scraped)} products. Chatbot now uses {reload_data.get('active_csv')}"
				)
				logger.info("Scrape completed; loaded=%s active_csv=%s", reload_data.get("loaded"), reload_data.get("active_csv"))
			except Exception as exc:
				logger.exception("Sidebar scraping failed")
				st.error(f"Scrape failed: {exc}")

	if st.button("Use All CSV Files"):
		try:
			reload_resp = httpx.post(
				f"{API_URL}/api/products/reload",
				params={"use_all": True},
				timeout=RELOAD_HTTP_TIMEOUT,
			)
			reload_resp.raise_for_status()
			reload_data = reload_resp.json()
			st.success(f"Chatbot now uses all CSV files. Loaded {reload_data.get('loaded', 0)} rows.")
			logger.info("Switched to all-CSV mode; loaded=%s", reload_data.get("loaded"))
		except Exception as exc:
			logger.exception("Switch to all-CSV mode failed")
			st.error(f"Could not enable all-CSV mode: {exc}")

	st.divider()
	st.markdown("### Product Catalog")
	try:
		stats = httpx.get(f"{API_URL}/api/products/stats", timeout=5.0).json()
		st.metric("Total Products", stats.get("total", "-"))
		st.metric("Brands", stats.get("brands", "-"))
		st.metric("Avg Price", f"Rs {stats.get('avg_price', 0):.0f}")
		st.metric("Avg Rating", f"{stats.get('avg_rating', 0):.1f}")
		st.caption(f"Mode: {stats.get('source_mode', 'single')}")
		st.caption(f"Using: {stats.get('active_csv', 'data/products.csv')}")
	except Exception:
		st.info("Stats unavailable")

	st.divider()
	st.markdown("### Human Support")
	st.info(
		"Returns, offers and complaints:\n\n"
		"Phone: +91-1800-266-1234\n\n"
		"Hours: Mon-Sat, 9AM-9PM"
	)

	if st.button("New Conversation"):
		st.session_state.session_id = str(uuid.uuid4())
		st.session_state.messages = []
		st.rerun()
