"""
Detects when the user's message should be escalated to a human agent.
Uses simple keyword matching - reliable, transparent, no LLM needed.
"""
from config.settings import get_settings

HANDOFF_PATTERNS = [
	"return",
	"refund",
	"exchange",
	"cancel order",
	"speak to human",
	"speak to agent",
	"real person",
	"offer",
	"discount code",
	"coupon",
	"promo code",
	"complaint",
	"complain",
	"broken",
	"damaged",
	"defective",
	"not working",
	"wrong product",
	"cheat",
	"fraud",
	"order status",
	"where is my order",
	"track my order",
]


def check_handoff(message: str) -> tuple[bool, str]:
	"""
	Returns (should_handoff: bool, response_message: str).
	Call this BEFORE sending to the LLM - saves API cost on escalations.
	"""
	msg_lower = message.lower()
	triggered = any(keyword in msg_lower for keyword in HANDOFF_PATTERNS)

	if triggered:
		phone = get_settings().support_phone
		response = (
			"I'd love to help with that! For this type of request, "
			"our dedicated customer care team is best placed to assist you.\n\n"
			f"Call us: {phone}\n"
			"Hours: Monday - Saturday, 9 AM - 9 PM IST\n\n"
			"Is there anything else I can help you with?"
		)
		return True, response

	return False, ""
