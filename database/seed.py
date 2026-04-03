"""
Inserts sample conversations into the DB to demonstrate the full workflow.
Run once: python -m database.seed
"""
import uuid

from database.connection import SessionLocal, engine
from database.models import Base, Conversation, Message


def seed():
	Base.metadata.create_all(bind=engine)
	db = SessionLocal()

	sample_data = [
		{
			"session": str(uuid.uuid4()),
			"messages": [
				(
					"user",
					"What lipstick shades does Lakme offer?",
					False,
					"product_search",
				),
				(
					"assistant",
					"Lakme offers shades like Ruby Red, Nude Beige, and "
					"Coral Pink in their Enrich Matte range, priced "
					"between Rs.220-Rs.350. Would you like more details?",
					False,
					"product_search",
				),
			],
		},
		{
			"session": str(uuid.uuid4()),
			"messages": [
				(
					"user",
					"What's the benefit of matte lipstick vs glossy?",
					False,
					"general_query",
				),
				(
					"assistant",
					"Matte lipstick offers longer wear and no transfer, "
					"while glossy adds shine and moisture. For formal "
					"occasions, matte. For a youthful look, glossy.",
					False,
					"general_query",
				),
			],
		},
		{
			"session": str(uuid.uuid4()),
			"messages": [
				(
					"user",
					"I want to return my lipstick.",
					False,
					"return_request",
				),
				(
					"assistant",
					"For returns, please contact our team at "
					"+91-1800-266-1234 (Mon-Sat, 9AM-9PM). "
					"They'll process it quickly!",
					True,
					"return_request",
				),
			],
		},
	]

	for item in sample_data:
		convo = Conversation(session_id=item["session"])
		db.add(convo)
		db.flush()
		for role, content, is_handoff, intent in item["messages"]:
			db.add(
				Message(
					conversation_id=convo.id,
					role=role,
					content=content,
					is_handoff=is_handoff,
					intent=intent,
				)
			)
	db.commit()
	db.close()
	print(f"Seeded {len(sample_data)} sample conversations.")


if __name__ == "__main__":
	seed()
