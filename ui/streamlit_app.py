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
					timeout=30.0,
				)
				resp.raise_for_status()
				data = resp.json()
				reply = data["reply"]
				is_handoff = data["is_handoff"]
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
	st.markdown("### Product Catalog")
	try:
		stats = httpx.get(f"{API_URL}/api/products/stats", timeout=5.0).json()
		st.metric("Total Products", stats.get("total", "-"))
		st.metric("Brands", stats.get("brands", "-"))
		st.metric("Avg Price", f"Rs {stats.get('avg_price', 0):.0f}")
		st.metric("Avg Rating", f"{stats.get('avg_rating', 0):.1f}")
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
