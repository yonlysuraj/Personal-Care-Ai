# Personal Care AI - Project Documentation

## 1. Project Purpose
This project is an AI-powered personal care assistant that combines:
- A chat interface for users (Streamlit)
- A backend API (FastAPI)
- Llama 3.3 70B via Groq for response generation
- Product knowledge from scraped CSV catalogs
- PostgreSQL for conversation history

The app supports:
- Dynamic product scraping from Myntra listing pages
- Selecting dataset source (single category CSV or merged all CSVs)
- Human handoff for support-related intents (returns, refund, complaints, etc.)

---

## 2. High-Level Folder Structure (Important Only)

```text
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

data/
  products_*.csv

scraper/
  myntra_scraper.py
  export.py

ui/
  streamlit_app.py

logs/
  api/
  ui/
```

---

## 3. Workflow (End-to-End)

### A. Chat Workflow
1. User sends a message from Streamlit UI.
2. UI calls `POST /api/chat`.
3. Backend checks handoff intent first.
4. If handoff triggered: return support message.
5. Else:
   - Fetch recent conversation history from PostgreSQL
   - Search product KB from active dataset source
   - Build system prompt + product context
   - Call Llama model (Groq)
6. Save user and assistant messages to DB.
7. Return assistant response to UI.

### B. Scrape Workflow
1. User provides Myntra URL + page count in sidebar.
2. Selenium scraper collects product cards page by page.
3. Scraped data exported to category CSV (`data/products_<category>.csv`).
4. UI calls `POST /api/products/reload`.
5. Backend updates active source for Product KB.
6. New chat responses use updated dataset immediately.

### C. Dataset Source Workflow
1. UI fetches available datasets via `GET /api/products/datasets`.
2. User selects source from dropdown.
3. On apply, backend reloads:
   - `use_all=true` for merged mode (`__ALL__`)
   - `csv_path=...` for single dataset mode
4. Stats panel uses `GET /api/products/stats`.

---

## 4. Core Functionalities

### Chat + Recommendations
- Conversational product assistant for personal-care catalog
- Multi-turn chat using stored conversation history
- Product-grounded recommendations from current dataset source

### Human Handoff
- Rule-based keyword detection for support operations
- Avoids sending support-specific issues to model
- Returns standard support contact/hours response

### Product Knowledge Base
- Loads CSVs into memory with caching
- Supports single-file mode and merged-all mode
- Keyword and category-aware product retrieval
- Dynamic category handling from available scraped data

### Scraper + Data Pipeline
- Scrapes listing pages with Selenium
- Extracts product metadata (name, brand, price, rating, URL, category, etc.)
- Exports clean CSV with numeric price column
- Deduplicates products by URL

### Observability
- Structured API/UI logs with dated log files
- Stepwise scraping logs for progress diagnostics

---

## 5. Important Files and What They Do

## `ui/streamlit_app.py`
- Main frontend application
- Sends chat requests to backend
- Sidebar controls for scraping and dataset source switching
- Displays catalog stats and chat messages

## `api/main.py`
- FastAPI application bootstrap
- Registers routes and CORS
- Creates DB tables on startup

## `api/routes/chat.py`
- Implements `POST /api/chat`
- Handles session/conversation lifecycle
- Runs handoff check and LLM flow
- Persists user/assistant messages

## `api/routes/products.py`
- Implements product utility endpoints:
  - `GET /api/products`
  - `GET /api/products/stats`
  - `GET /api/products/datasets`
  - `POST /api/products/reload`
- Controls active product source mode

## `chatbot/product_kb.py`
- Loads and caches product CSV data
- Supports merged default mode (`__ALL__`)
- Performs product search and category filtering
- Formats product context for prompt injection

## `chatbot/groq_client.py`
- Builds final model message payload
- Calls Groq chat completion API with Llama model

## `chatbot/handoff.py`
- Contains escalation keywords and handoff response template

## `chatbot/prompt_templates.py`
- Defines system prompt rules and response constraints

## `scraper/myntra_scraper.py`
- Browser automation for listing-page scraping
- Page-level extraction and stepwise logging
- Writes category-specific CSV outputs

## `scraper/export.py`
- Converts scraped records to CSV
- Cleans prices to numeric field
- Deduplicates by product URL

## `database/connection.py`
- SQLAlchemy engine/session management
- DB health check helper

## `database/models.py`
- ORM models for conversations and messages (plus product schema)

## `config/settings.py`
- Centralized env-based configuration
- Environment-specific DB URL selection

## `config/logging_setup.py`
- Log formatter and dated log file handlers

---

## 6. Default Runtime Behavior (Current)
- Default source mode: merged all CSVs (`__ALL__`)
- Dataset can be switched from UI dropdown
- Scraping a category file can be applied immediately to chat source
- Conversation state persists in PostgreSQL by `session_id`

---

## 7. Typical Run Order
1. Start PostgreSQL (local or docker)
2. Start FastAPI backend
3. Start Streamlit UI
4. Optionally scrape a new category dataset
5. Select dataset source and start chatting
