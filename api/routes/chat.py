from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import ChatRequest, ChatResponse
from chatbot.groq_client import get_chat_response
from chatbot.handoff import check_handoff
from config.logging_setup import get_logger
from database.connection import get_db
from database.models import Conversation, Message

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger("api.routes.chat", app_name="api")


def get_or_create_conversation(session_id: str, db: Session) -> Conversation:
	"""Get existing conversation or create a new one for this session_id."""
	convo = db.query(Conversation).filter(Conversation.session_id == session_id).first()
	if not convo:
		convo = Conversation(session_id=session_id)
		db.add(convo)
		db.commit()
		db.refresh(convo)
	return convo


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
	logger.info("Chat request received for session_id=%s", request.session_id)
	# 1. Check for human handoff first.
	is_handoff, handoff_msg = check_handoff(request.message)

	convo = get_or_create_conversation(request.session_id, db)

	# 2. Save user message.
	user_msg = Message(
		conversation_id=convo.id,
		role="user",
		content=request.message,
		is_handoff=False,
	)
	db.add(user_msg)
	db.commit()

	if is_handoff:
		reply = handoff_msg
		intent = "escalation"
		logger.info("Handoff triggered for session_id=%s", request.session_id)
	else:
		# 3. Fetch history for context.
		history = [
			{"role": m.role, "content": m.content}
			for m in convo.messages[-20:]
			if m.role in ("user", "assistant")
		]

		# 4. Call LLM.
		try:
			reply = get_chat_response(request.message, history)
			intent = "general"
		except Exception as exc:
			logger.exception("LLM error for session_id=%s", request.session_id)
			raise HTTPException(status_code=503, detail=f"LLM error: {exc}") from exc

	# 5. Save assistant response.
	ai_msg = Message(
		conversation_id=convo.id,
		role="assistant",
		content=reply,
		is_handoff=is_handoff,
		intent=intent,
	)
	db.add(ai_msg)
	db.commit()
	logger.info("Assistant response saved for session_id=%s", request.session_id)

	return ChatResponse(
		reply=reply,
		session_id=request.session_id,
		is_handoff=is_handoff,
		intent=intent,
	)
