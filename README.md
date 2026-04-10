# Personal Care AI Assistant

This project is an advanced AI-powered personal-care assistant that combines an interactive frontend, a scalable backend, a live data scraper, and a dynamic Retrieval-Augmented Generation (RAG) pipeline to deliver grounded, hallucination-free product recommendations and responsive customer service.

![Workflow](WorkFlow.png)

## Core Architecture

- **Backend:** FastAPI
- **Frontend:** Streamlit
- **LLM Engine:** Groq API (Llama 3.1 / 3.3) with rate-limit fallback handling
- **Database:** PostgreSQL (SQLAlchemy) for persistent conversation storage
- **Data Ingestion:** Selenium web scraper (local-only) with dynamic category discovery

## Key Features

- **Grounded Product Recommendations:** Chat assistant powered by a native Pandas-based RAG pipeline that filters and injects context directly into the LLM prompt.
- **Dynamic Category Handling:** The AI automatically detects product domains (e.g., "lipstick", "beard serum") from user queries using token intersection against the live dataset, enabling complex multi-category queries without hardcoded logic.
- **Human Handoff Safety:** Intent-based detection intercepts sensitive requests (returns, complaints, refunds) *before* LLM generation to prevent policy hallucination and ensure enterprise-level safety.
- **Live Data Integration:** An integrated sidebar scraper runs real-time Selenium extraction on e-commerce listings, complete with stepwise UI progress bars.
- **Seamless Dataset Control:** Admins can instantly switch the active AI Knowledge Base via a UI dropdown. The system defaults to **Merged Mode**, synthesizing all locally scraped category CSVs for a massive, comprehensive catalog.
- **Resilient API:** Configured with a `GROQ_API_KEY_FALLBACK` to automatically switch API keys if rate limits are exceeded.

## Tech Stack

- Python 3.14
- FastAPI
- Streamlit
- SQLAlchemy + PostgreSQL
- Groq SDK (Llama models)
- Selenium + webdriver-manager + BeautifulSoup + Pandas

## Project Structure

```text
project-root/
	api/
		main.py
		schemas.py
		routes/
			chat.py
			products.py
	chatbot/
		groq_client.py
		handoff.py
		product_kb.py
		prompt_templates.py
	config/
		settings.py
		logging_setup.py
	database/
		connection.py
		models.py
		seed.py
	scraper/
		myntra_scraper.py
		export.py
	ui/
		streamlit_app.py
	data/
		products_*.csv
	logs/
		api-YYYY-MM-DD.log
		ui-YYYY-MM-DD.log
```

## Setup

1. Clone and enter project directory.
2. Create virtual environment.
3. Install dependencies.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create `.env` in project root:

```env
GROQ_API_KEY=your_groq_key
GROQ_API_KEY_FALLBACK=your_secondary_groq_key

LOCAL_DATABASE_URL=postgresql://postgres:password@localhost:5432/personal_care_db
PRODUCTION_DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
ENVIRONMENT=development
SUPPORT_PHONE=+91-1800-266-1234
ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000
```

## Run Locally

Start FastAPI:

```powershell
venv\Scripts\activate
uvicorn api.main:app --reload --port 8000
```

Start Streamlit:

```powershell
venv\Scripts\activate
streamlit run ui/streamlit_app.py
```

Open:

- UI: `http://localhost:8501`
- API docs: `http://localhost:8000/api/docs`

## How Data Source Works

The system dynamically lists all `.csv` files stored in `data/`, making them selectable in the Streamlit Sidebar.

### Single CSV mode
- When you use the scraper, it writes a new category file in `data/` (for example `products_nail_polish.csv`).
- A backend automatically registers this file. Selecting it sets the RAG context strictly to this single category, perfect for constrained testing.

### All CSV mode (Merged Mode - Default)
- By selecting `All CSV Files (merged)` from the dropdown, the backend leverages pandas to concatenate every `products_*.csv` file in the folder.
- This creates a massive, multi-domain knowledge base allowing the chatbot to answer complex, mixed-domain queries.

## Sidebar Scraping

In the Streamlit sidebar:

1. Paste a Myntra listing URL.
2. Set the desired page count limit.
3. Click `Scrape Products`. You will see a real-time progress bar tracking stepwise validation.
4. The system automatically structures and saves the data into `data/products_[category].csv`, immediately refreshing the UI dropdown available datasets.

Examples:

- Lipstick: `https://www.myntra.com/personal-care?f=Categories%3ALipstick`
- Perfume: `https://www.myntra.com/personal-care?f=Categories%3APerfume`
- Nail Polish: `https://www.myntra.com/personal-care?f=Categories%3ANail%20Polish`
- Massage Oils: `https://www.myntra.com/personal-care?f=Categories%3AMassage%20Oils`

## API Endpoints

- `POST /api/chat`
	- Body: `{ "message": "...", "session_id": "..." }`
	- Returns assistant reply and handoff status

- `GET /api/products/datasets`
	- Gets a JSON list of all available `.csv` mapping targets, returning the user-friendly filename alongside full absolute paths.
- `GET /api/products`
	- Retrieves the current state of products based on the session's active dataset.
- `GET /api/products/stats`
	- Returns catalog metadata, total row count, available categories, and the currently active mode.
- `POST /api/products/reload`
	- Syncs the Streamlit UI state with the backend dataset configuration. Pass `csv_path` to bind context to a single file, or `use_all=true` for Merged Mode.

- `GET /api/health`
	- Returns app status + DB connectivity

## Logging

Dated logs are written to:

- `logs/api-YYYY-MM-DD.log`
- `logs/ui-YYYY-MM-DD.log`

These logs include chat requests, scrape/reload events, and error traces.

## Troubleshooting

- Timeout in chat (`timed out`) or `503 Service Unavailable`:
	- If rate limited on Groq, the backend will auto-failover to `GROQ_API_KEY_FALLBACK`.
	- If both keys expire, ensure your `.env` contains valid, active API keys with available balance.
	- Ensure the backend (`uvicorn`) is running and not stuck waiting on the database.

- Category not answering multi-domain queries (e.g. asking for beard serum and lipstick):
	- Ensure the Streamlit sidebar dropdown is set to `All CSV Files (merged)`.
	- Ensure both `products_beard_serum.csv` and `products_lipstick.csv` exist in the `data/` folder.
	- The system dynamic token matching logic automatically cross-references these!

- Streamlit import error (`No module named config`):
	- Run from project root
	- Restart Streamlit after code changes

- Scrape fails with invalid URL/session errors:
	- Use a valid Myntra listing URL
	- Reduce page count
	- Retry after a short delay

## Notes

- Scraper is local-only (not for serverless runtime)
- Streamlit should be hosted separately from the API backend in production
- Serverless databases may have cold start delays
