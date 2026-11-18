# Customer Churn Prediction Agent

This project delivers a lightweight end-to-end churn prediction MVP in Python. It loads an IBM Telco-style churn dataset when available, otherwise uses a bundled sample dataset and a deterministic synthetic fallback. The app preprocesses the data, trains and compares Logistic Regression and Random Forest models, scores customers, assigns Low/Medium/High risk bands, explains the strongest churn drivers, surfaces the highest-risk accounts, and recommends retention actions.

## Features

- Data loading with fallback chain: real IBM Telco CSV -> bundled sample CSV -> deterministic synthetic dataset
- Preprocessing for mixed numeric and categorical features
- Model evaluation for both Logistic Regression and Random Forest
- Probability scoring and risk segmentation
- Feature importance and explanation output
- High-risk customer identification
- Deterministic retention recommendations
- Streamlit UI with Dashboard, Customers, and Predict pages
- FastAPI REST backend for health, metrics, feature importance, customers, and predictions
- Dashboard metric cards, confusion matrix, feature importance, and risk distribution
- Filterable/sortable customer table with risk badges and churn probabilities
- Single-customer prediction form with deterministic model explanation and retention recommendations
- Unit tests for the core pipeline and API behavior

## Project structure

- `app.py`: Streamlit UI with Dashboard, Customers, and Predict pages
- `api.py`: FastAPI entry point
- `churn_app/api.py`: API schemas, CORS, endpoints, and pipeline integration
- `frontend/`: responsive dependency-free product UI served by FastAPI
- `churn_app/data_loader.py`: dataset loader and synthetic generator
- `churn_app/pipeline.py`: churn preprocessing, model training, scoring, and recommendations
- `data/WA_Fn-UseC_-Telco-Customer-Churn.csv`: real IBM Telco dataset used by the demo when present
- `data/telco_sample.csv`: compact fallback sample dataset
- `tests/test_pipeline.py`: validation tests

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal (typically `http://localhost:8501`).

## Run the REST API

```bash
uvicorn api:app --reload --port 8000
```

The API runs at `http://localhost:8000`. Interactive OpenAPI docs are available at
`http://localhost:8000/docs`. CORS allows local frontend development from
`http://localhost:3000` and `http://127.0.0.1:3000`.

The product UI is available at `http://localhost:8000/frontend/` when the API is
running. It includes a responsive social-style workspace: Home with activity and
quick actions, Inbox with customer conversations, customer discovery with
search/filter/sort, customer risk detail/prediction workflow, and an AI Copilot
that uses the real `/predict` and cancelable `/explain` streaming endpoints. It
is plain HTML/CSS/JavaScript, so no Node build step is required; Streamlit remains
available as an alternate Python UI.

Endpoints:

- `GET /health`
- `GET /metrics`
- `GET /feature-importance?top_n=10`
- `GET /customers?risk=High&limit=50&offset=0`
- `POST /predict` with a JSON customer profile matching the fields in `churn_app.api.CustomerInput`
- `POST /explain` with the same profile; returns `text/event-stream` events (`token`, then `done`) for a progressive explanation
- `GET /explanation-logs?limit=50` for locally persisted explanation audit records

No Next.js project is included because this folder has no existing Node setup; the
FastAPI contract is ready for a frontend to consume, while the Streamlit UI remains
the runnable local frontend.

### Streaming explanation consumption

The `/explain` endpoint is intentionally deterministic and uses the trained model's
feature explanation plus retention recommendation. It does not pretend to be an LLM
and does not require an API key. A browser frontend can use `fetch`, read the
response body's `ReadableStream`, split on blank lines, and process `data:` JSON
payloads until the `event: done` message. If a future provider is configured, it
should be an explicit optional integration with a safe fallback to this model
explanation.

The stream emits an `error` event for handled scoring/persistence failures and
checks `request.is_disconnected()` before each event and before audit persistence.
Clients can cancel with `AbortController`; cancellation/disconnect stops the
generator and does not persist a partial explanation.

Completed explanations are persisted to `data/explanation_logs.db` using SQLite
with parameterized writes. Set `CHURN_AUDIT_DB` to use another local SQLite path.
Supabase is deliberately not required or initialized without explicit application
configuration; no secrets are bundled. The current project has no Next.js frontend,
so Markdown rendering and browser text-to-speech remain frontend responsibilities
for a future consumer. A frontend should pass an `AbortController.signal` to
`fetch('/explain')`; aborting it cancels the request, and server disconnect checks
stop generation without writing a partial audit record.

## Run tests

```bash
pytest -q
```

## Notes

- The app intentionally avoids secrets or cloud dependencies.
- The included IBM Telco CSV contains 7,043 customer records and is loaded automatically by its expected filename.
- If the IBM Telco CSV is removed, the loader uses the compact bundled sample and then a deterministic synthetic dataset, so the demo remains runnable offline.
- API metrics are computed from the trained pipeline at startup; they are not hard-coded.
