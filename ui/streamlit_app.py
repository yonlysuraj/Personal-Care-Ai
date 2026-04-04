"""
Streamlit Chat UI.

Calls the FastAPI backend via HTTP.
Session ID is stored in session_state so each browser tab has one conversation.
"""

import os
from pathlib import Path
import sys
from time import perf_counter
import uuid

import httpx
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

from config.logging_setup import get_logger, silence_console_logging

API_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")
silence_console_logging(["streamlit", "streamlit.runtime", "streamlit.web"])
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
				data = None
				for attempt in range(2):
					try:
						call_started = perf_counter()
						logger.info("Sending chat request session_id=%s attempt=%s", st.session_state.session_id, attempt + 1)
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
						elapsed_ms = int((perf_counter() - call_started) * 1000)
						logger.info(
							"Chat response received session_id=%s attempt=%s status=%s elapsed_ms=%s",
							st.session_state.session_id,
							attempt + 1,
							resp.status_code,
							elapsed_ms,
						)
						break
					except httpx.ReadTimeout:
						if attempt == 0:
							logger.warning(
								"Chat timeout on first attempt; retrying for session_id=%s",
								st.session_state.session_id,
							)
							continue
						raise

				reply = data["reply"] if data else "Sorry, no response received."
				is_handoff = data["is_handoff"] if data else False
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
	st.markdown("### Dataset Source")
	try:
		dataset_info = httpx.get(f"{API_URL}/api/products/datasets", timeout=5.0).json()
		datasets = dataset_info.get("datasets", [])
		active_dataset = dataset_info.get("active_dataset", "__ALL__")
		options = ["__ALL__"] + datasets
		if active_dataset not in options:
			options.append(active_dataset)

		# Keep UI selection aligned with backend source unless user explicitly applies a new choice.
		if "last_applied_dataset" not in st.session_state:
			st.session_state.last_applied_dataset = active_dataset
		if st.session_state.last_applied_dataset != active_dataset:
			st.session_state.selected_dataset = active_dataset
			st.session_state.last_applied_dataset = active_dataset
		if "selected_dataset" not in st.session_state or st.session_state.selected_dataset not in options:
			st.session_state.selected_dataset = active_dataset

		selected_dataset = st.selectbox(
			"Choose dataset",
			options=options,
			index=options.index(st.session_state.selected_dataset),
			format_func=lambda x: "All CSV Files (merged)" if x == "__ALL__" else x,
		)
		st.session_state.selected_dataset = selected_dataset
		st.caption(f"Active now: {active_dataset}")

		if st.button("Apply Dataset"):
			try:
				progress_text = st.empty()
				progress_text.info("Switching dataset source...")
				progress = st.progress(0)
				progress.progress(20)
				reload_started = perf_counter()
				if selected_dataset == "__ALL__":
					progress.progress(45)
					reload_resp = httpx.post(
						f"{API_URL}/api/products/reload",
						params={"use_all": True},
						timeout=RELOAD_HTTP_TIMEOUT,
					)
				else:
					progress.progress(45)
					reload_resp = httpx.post(
						f"{API_URL}/api/products/reload",
						params={"csv_path": f"data/{selected_dataset}"},
						timeout=RELOAD_HTTP_TIMEOUT,
					)
				progress.progress(80)
				reload_resp.raise_for_status()
				reload_data = reload_resp.json()
				elapsed_ms = int((perf_counter() - reload_started) * 1000)
				new_active = Path(reload_data.get("active_csv", "")).name or selected_dataset
				st.session_state.selected_dataset = new_active
				st.session_state.last_applied_dataset = new_active
				progress.progress(100)
				progress_text.empty()
				st.success(
					f"Source updated. Mode: {reload_data.get('source_mode')} | Active: {reload_data.get('active_csv')}"
				)
				logger.info(
					"Dataset switched source_mode=%s active_csv=%s elapsed_ms=%s",
					reload_data.get("source_mode"),
					reload_data.get("active_csv"),
					elapsed_ms,
				)
			except Exception as exc:
				progress_text.empty()
				logger.exception("Dataset switch failed")
				st.error(f"Could not switch dataset: {exc}")
	except Exception:
		st.info("Dataset list unavailable")

	st.divider()
	st.markdown("### Scrape Myntra")
	scrape_url = st.text_input(
		"Listing URL",
		value="https://www.myntra.com/personal-care?f=Categories%3ALipstick",
	)
	page_count = st.slider("Pages", min_value=1, max_value=10, value=3)

	if st.button("Scrape Products"):
		progress_text = st.empty()
		progress = st.progress(0)
		try:
			scrape_started = perf_counter()
			logger.info("Scrape triggered url=%s pages=%s", scrape_url, page_count)
			from scraper.myntra_scraper import category_to_slug, detect_category, scrape

			progress_text.info("Step 1/4: Detecting category from URL...")
			progress.progress(10)
			category, _ = detect_category(scrape_url)
			csv_path = ROOT_DIR / "data" / f"products_{category_to_slug(category)}.csv"

			progress_text.info("Step 2/4: Scraping Myntra pages...")
			progress.progress(25)
			scraped = scrape(url=scrape_url, max_pages=page_count, output_path=str(csv_path))

			progress_text.info("Step 3/4: Reloading chatbot dataset...")
			progress.progress(80)
			reload_resp = httpx.post(
				f"{API_URL}/api/products/reload",
				params={"csv_path": str(csv_path)},
				timeout=RELOAD_HTTP_TIMEOUT,
			)
			reload_resp.raise_for_status()
			reload_data = reload_resp.json()
			elapsed_ms = int((perf_counter() - scrape_started) * 1000)
			new_active = Path(reload_data.get("active_csv", "")).name
			if new_active:
				st.session_state.selected_dataset = new_active
				st.session_state.last_applied_dataset = new_active

			progress_text.info("Step 4/4: Done")
			progress.progress(100)
			st.success(
				f"Scraped {len(scraped)} products. Chatbot now uses {reload_data.get('active_csv')}"
			)
			logger.info(
				"Scrape completed loaded=%s active_csv=%s elapsed_ms=%s",
				reload_data.get("loaded"),
				reload_data.get("active_csv"),
				elapsed_ms,
			)
		except Exception as exc:
			logger.exception("Sidebar scraping failed")
			st.error(f"Scrape failed: {exc}")
		finally:
			progress_text.empty()
			progress.empty()

	st.divider()
	st.markdown("### Product Catalog")
	try:
		stats_started = perf_counter()
		stats = httpx.get(f"{API_URL}/api/products/stats", timeout=5.0).json()
		logger.info("Stats fetched mode=%s active_csv=%s elapsed_ms=%s", stats.get("source_mode"), stats.get("active_csv"), int((perf_counter() - stats_started) * 1000))
		st.metric("Total Products", stats.get("total", "-"))
		st.metric("Brands", stats.get("brands", "-"))
		st.metric("Avg Price", f"Rs {stats.get('avg_price', 0):.0f}")
		st.metric("Avg Rating", f"{stats.get('avg_rating', 0):.1f}")
		st.caption(f"Mode: {stats.get('source_mode', 'single')}")
		st.caption(f"Using: {stats.get('active_csv', '__ALL__')}")
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
