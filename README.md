# Personal Care AI Assistant

This project is an AI-powered personal-care assistant that combines:

- FastAPI backend
- Streamlit chat UI
- Groq LLM (Llama 3.3 70B)
- PostgreSQL conversation storage
- Myntra scraper (local-only) for building a product knowledge base from CSV files

The app supports both:

- Single CSV mode (use one dataset)
- All CSV mode (merge all datasets in the `data/` folder)

## Features

- Chat assistant for personal-care product discovery and recommendations
- Human handoff detection for support/returns/offers/complaints
- Sidebar scraping from any Myntra listing URL
- Auto-generated category CSV files (for example `products_perfume.csv`)
- Runtime source switch:
	- Use latest scraped file
	- Use all CSV files together
- Product catalog stats in UI
- Dated application logs in `logs/`

## Tech Stack

- Python 3.14
- FastAPI
- Streamlit
- SQLAlchemy + PostgreSQL
- Groq SDK
- Selenium + webdriver-manager + BeautifulSoup + pandas

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
		products.csv
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

### Single CSV mode

- Scraping from sidebar writes a category file in `data/` (for example `products_nail_polish.csv`)
- Backend reloads that file and chat answers from it

### All CSV mode

- Click `Use All CSV Files` in sidebar
- Backend merges all `products_*.csv` in `data/`
- Chat answers from combined catalog

Note: if you scrape a new file while in all mode, source switches to that new single file. Click `Use All CSV Files` again to re-enable merged mode.

## Sidebar Scraping

In Streamlit sidebar:

1. Paste Myntra listing URL
2. Set page count
3. Click `Scrape Products`
4. Optionally click `Use All CSV Files`

Examples:

- Lipstick: `https://www.myntra.com/personal-care?f=Categories%3ALipstick`
- Perfume: `https://www.myntra.com/personal-care?f=Categories%3APerfume`
- Nail Polish: `https://www.myntra.com/personal-care?f=Categories%3ANail%20Polish`
- Massage Oils: `https://www.myntra.com/personal-care?f=Categories%3AMassage%20Oils`

## API Endpoints

- `POST /api/chat`
	- Body: `{ "message": "...", "session_id": "..." }`
	- Returns assistant reply and handoff status

- `GET /api/products`
	- Optional query: `limit`, `brand`

- `GET /api/products/stats`
	- Returns catalog stats + active source mode

- `POST /api/products/reload`
	- Query params:
		- `csv_path` for single-file mode
		- `use_all=true` for merged mode

- `GET /api/health`
	- Returns app status + DB connectivity

## Logging

Dated logs are written to:

- `logs/api-YYYY-MM-DD.log`
- `logs/ui-YYYY-MM-DD.log`

These logs include chat requests, scrape/reload events, and error traces.

## Troubleshooting

- Timeout in chat (`timed out`):
	- Retry once
	- Ask shorter query
	- Ensure backend is running

- Category not appearing in mixed query:
	- Click `Use All CSV Files`
	- Confirm `Mode: all` in sidebar
	- Ensure corresponding `products_*.csv` exists in `data/`

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
