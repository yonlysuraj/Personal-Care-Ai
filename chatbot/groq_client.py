"""
Groq API wrapper.
- Sends conversation history + product context to Llama 3.3 70B
- Returns the assistant's response text
"""

from groq import Groq

from chatbot.product_kb import format_products_for_prompt, search_products
from chatbot.prompt_templates import build_system_prompt
from config.settings import get_settings

_client: Groq | None = None


def get_groq_client() -> Groq:
	global _client
	if _client is None:
		_client = Groq(api_key=get_settings().groq_api_key)
	return _client


def get_chat_response(
	user_message: str,
	history: list[dict],
	max_tokens: int = 512,
) -> str:
	"""
	Builds the full message list and calls Groq.
	history = previous turns (fetched from PostgreSQL in the API layer)
	"""
	relevant = search_products(user_message)
	product_context = format_products_for_prompt(relevant)
	system_prompt = build_system_prompt(product_context)

	messages = [{"role": "system", "content": system_prompt}]
	messages.extend(history[-10:])
	messages.append({"role": "user", "content": user_message})

	response = get_groq_client().chat.completions.create(
		model="llama-3.3-70b-versatile",
		messages=messages,
		max_tokens=max_tokens,
		temperature=0.7,
	)

	content = response.choices[0].message.content
	return content if content is not None else ""
