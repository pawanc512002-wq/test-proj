# RFP Cloud — README

> Single-user RFP management POC
> Backend: **FastAPI** (JSON file storage)
> Frontend: **Minimal Streamlit UI** (talks to FastAPI)
> Lightweight AI support via **OpenAI** (optional) or deterministic local parsers (default).

This README explains how the project is organized, how to set it up and run locally, how data is stored and managed, what each file/module does, how to enable the AI features, and how to simulate comparisons & recommendations.

---

## Quick summary (what this repo provides)

* Create RFPs from **natural language** (Streamlit → FastAPI → AI parser or local parser).
* Manage vendors (add/list).
* "Send" RFPs to vendors (simulated outbound stored in `outbox.json`).
* Receive vendor proposals via a simulated inbound webhook (Streamlit form or POST to FastAPI), auto-parse proposals and persist them.
* Compare proposals for an RFP using deterministic scoring + optional AI refinement; return a recommended vendor and per-proposal scores.
* All persistent data is saved as JSON files so you can inspect and back them up easily.

---

## Setup (local)

> These instructions assume you have Python 3.10+ installed. We recommend using a virtual environment.

1. **Clone the repo** (or copy files into a directory):

```bash
git clone <your-repo-url>
cd <repo-root>
```

2. **Where to create the venv**

Create the virtual environment at the **repo root** (this keeps the venv next to backend & frontend code and makes paths simple):

```bash
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell)
.\\.venv\\Scripts\\Activate.ps1
# or Windows (cmd)
.\\.venv\\Scripts\\activate
```

3. **Install backend requirements (FastAPI app)**

```bash
cd backend            # if your backend folder is named backend
pip install -r requirements.txt
# (requirements.txt should include fastapi, uvicorn, python-dotenv, openai (optional))
```

4. **Install frontend requirements (Streamlit app)**

Open a second terminal (or stay in same venv) and:

```bash
cd streamlit_frontend_or_root_folder  # path where your Streamlit app (app.py) lives
pip install -r requirements.txt      # requirements for Streamlit (streamlit, requests, python-dotenv)
```

> If the repo is organized as a hybrid where backend & frontend live under the same project folder, you may only need one venv and one `requirements.txt` that contains both backend & frontend deps; adjust accordingly.

5. **Environment variables**

Copy `.env.example` to `.env` and set any values you need:

```
# .env
OPENAI_API_KEY=sk-xxxx           # optional, if you want AI parsing via OpenAI
API_URL=http://localhost:5000    # Streamlit uses this to call FastAPI endpoints
```

6. **Run the backend (FastAPI)**

From the backend folder:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```


7. **Run the frontend (Streamlit)**

From the folder containing `app.py` (Streamlit):

```bash
streamlit run app.py
```

* Streamlit usually opens at [http://localhost:8501](http://localhost:8501)

---

## Files & What They Do

This section maps the core files/modules to their responsibilities so you can quickly understand and modify them.

### `backend/` (FastAPI app)

* **`main.py`**

  * All FastAPI endpoints:

    * `POST /api/v1/rfps` — create RFP (parsing via AI or mock)
    * `GET /api/v1/rfps` — list RFPs
    * `GET /api/v1/rfps/{id}` — get RFP
    * `POST /api/v1/vendors` — add vendor
    * `GET /api/v1/vendors` — list vendors
    * `POST /api/v1/rfps/{id}/send` — simulate sending RFP to selected vendors (writes to `outbox.json`)
    * `POST /api/v1/email/inbound` — inbound webhook: accept vendor responses, parse them, save proposals
    * `GET /api/v1/rfps/{id}/proposals` — list proposals for an RFP
    * `POST /api/v1/rfps/{id}/compare` — compute scores & return recommendation
  * Uses the `storage` module for read/write of JSON files and `ai_helpers` for parsing/scoring.

* **`storage.py`**

  * Utilities to read / write JSON files.
  * Keeps data folder such as `backend/data/rfps.json`, `vendors.json`, `proposals.json`, `outbox.json`.
  * Ensures the files exist and returns sensible defaults (e.g., `[]` for lists).

* **`models.py`**

  * Pydantic models / request/response types that validate incoming requests (e.g., `RFPCreateRequest`, `VendorCreate`, `ProposalInbound`).
  * Response models used in route `response_model` declarations (optional but recommended).

* **`ai_helpers.py`**

  * Local deterministic parsers:

    * `parse_rfp_from_text_mock(text)` — extracts items, budget, delivery, warranty, payment terms with regex heuristics.
    * `parse_proposal_from_text_mock(text)` — extracts total price, delivery days, warranty, notes.
  * Scoring:

    * `score_proposal(parsed, rfp)` — deterministic scoring combining inverse price, delivery, and warranty.
  * Optional OpenAI wrapper:

    * `call_openai_json(prompt)` — calls OpenAI and returns JSON (must set `OPENAI_API_KEY`).
    * `OPENAI_KEY` and `OPENAI_MODEL` are read from environment.

> Tip: Keep `ai_helpers.py` small and test its mock functions extensively with unit tests — they’re the main place where parsing logic lives.

---

### `streamlit/` or Streamlit UI file (e.g. `app.py`)

* Presents a friendly multi-tab UI:

  * **Create RFP** — NL input + Create button. Calls `POST /api/v1/rfps`.
  * **Vendors** — Form to add vendor; list vendors (calls `POST /api/v1/vendors`, `GET /api/v1/vendors`).
  * **Send RFP** — Choose RFP and vendors, press Send (calls `POST /api/v1/rfps/{id}/send`).
  * **Inbound (simulate)** — Form to emulate vendor email reply (calls `POST /api/v1/email/inbound`).
  * **Compare** — Select RFP, press Compare to call `POST /api/v1/rfps/{id}/compare` and view results.
  * **Admin** — Download backend data as a ZIP or view raw JSON files (reads `backend/data/*.json` using relative path).
* Streamlit uses `API_URL` environment variable (default `http://localhost:5000`) to call the backend.

---

## Data files & data management

All persistent data is stored as JSON files under the backend `data/` folder:

* `backend/data/rfps.json` — list of RFP objects
* `backend/data/vendors.json` — list of vendor objects
* `backend/data/proposals.json` — list of parsed proposals
* `backend/data/outbox.json` — simulated outbound emails sent to vendors

**You can:**

* Inspect JSON files directly (they are human-readable).
* Download a ZIP from the Streamlit Admin tab that packages all `*.json` files.
* Back up the `/data` folder manually or copy to S3 if needed.
* Reset/clear the data by truncating the JSON arrays (e.g., `[]`) or using a provided "wipe data" admin action in Streamlit.

---

## AI integration

* **Optional**. The app works without any AI key — it falls back to local deterministic parsers.
* To enable OpenAI:

  1. Add your key to `.env` or export `OPENAI_API_KEY` in your shell.
  2. `ai_helpers.call_openai_json(prompt)` will be used where available; OpenAI should return strictly formatted JSON.
  3. Prompt design:

     * For RFP parsing: instruct model to return strict JSON `{title, items: [...], budget, delivery_days, ...}` only.
     * For proposal parsing: ask for JSON `{total_price, delivery_days, warranty_months, notes}`.
  4. In `ai_helpers.call_openai_json()` use `temperature=0` and validate the returned JSON server-side (Pydantic) before persisting.

**Security & cost notes**

* OpenAI calls may cost tokens; instrument logging and consider rate-limits and quota.
* Validate LLM outputs — never trust raw text; convert to JSON and validate types/fields.

---

## Simulating compare & recommendation

**How it works**

* The backend stores parsed proposals with `parsed` JSON and an optional `score` field.
* When `POST /api/v1/rfps/{rfp_id}/compare` is invoked:

  * For proposals missing a `score`, the backend computes one using `ai_helpers.score_proposal(parsed, rfp)`.
  * The backend returns the `best` proposal (max score) and the list of proposals with scores.

**How to test**

1. Create RFP (Streamlit).
2. Add vendor(s).
3. Send RFP (simulated).
4. Submit inbound proposals either:

   * Using the Streamlit *Inbound (simulate)* tab (fill subject with `RFPID:<rfp-id>` to auto-link), or
   * Using `curl` / Postman to call:

     ```bash
     curl -X POST http://localhost:5000/api/v1/email/inbound \
       -H 'Content-Type: application/json' \
       -d '{"from_email":"sales@vendor.example","subject":"Re: RFPID:<rfp-id>","body":"We can supply for $45000. Delivery 25 days. Warranty 12 months."}'
     ```
5. Click **Compare** in Streamlit to call `POST /api/v1/rfps/{id}/compare` and view results.

**Interpreting results**

* Score is higher for lower prices, faster delivery, and longer warranty (as implemented in `ai_helpers.score_proposal`).
* `best` field is the best-scoring proposal object.

---

## UI improvements & "cool features" you can add (Streamlit)

Here are suggestions to make the UI look and feel better:

* **Responsive layout** — use `st.columns()` and card-style boxes for RFP summary, vendor cards, proposals.
* **Progress indicators** — show spinners while network calls happen (`with st.spinner("Parsing..."):`).
* **Status badges** — indicate completeness or "missing fields" with colored labels.
* **Inline editing** — allow editing an RFP’s extracted fields (title/items) before saving.
* **File uploads** — allow uploading vendor attachments (PDF/CSV), save them to `backend/data/attachments/` and run OCR/parsing offline.
* **Charts** — use `st.bar_chart()` to show price comparisons visually.
* **Search & filters** — add search for RFPs and filter proposals by vendor or price range.
* **Download individual proposal** — add per-proposal “Download JSON” buttons.
* **Theming** — use Streamlit's theme settings to match your product colors and fonts.

---

## Troubleshooting & tips

* If Streamlit can't reach the API, ensure `API_URL` is correct and backend is running (ports must match).
* If you see `OpenAI key not set` errors, either set `OPENAI_API_KEY` or rely on mock parsers.
* If you need to start fresh, delete `backend/data/*.json` (or set them to `[]`) and restart the services.
* For Windows users: in PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` if you hit activation issues with venv scripts.

---

## Example curl commands

Create RFP (server will parse with mock or OpenAI):

```bash
curl -X POST http://localhost:5000/api/v1/rfps \
  -H "Content-Type: application/json" \
  -d '{"text":"I need 10 laptops 16GB, budget $30,000, delivery 20 days."}'
```

Simulate inbound vendor proposal:

```bash
curl -X POST http://localhost:5000/api/v1/email/inbound \
  -H "Content-Type: application/json" \
  -d '{"from_email":"sales@vendor.com","subject":"Re: RFPID:<rfp-id>","body":"We offer $25000, delivery in 18 days, warranty 12 months."}'
```

Compare proposals for an RFP:

```bash
curl -X POST http://localhost:5000/api/v1/rfps/<rfp-id>/compare
```

---

## Extending this POC

* Replace JSON-file storage with PostgreSQL + SQLAlchemy for durability & concurrency.
* Add authentication and multi-user support.
* Persist attachments to object storage (S3) and parse using OCR (Tesseract or cloud OCR).
* Build richer prompts and validation for AI parsing (schema-based, with fallback/manual edit UI).

---
