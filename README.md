# AEGIS — Intelligent Energy & Equipment Monitoring

Contextual anomaly detection for chiller equipment, built for the YUKTHI 2026
"Intelligent Energy & Equipment Monitoring" hackathon challenge.

## Status: complete (backend + frontend)

## Backend (`/backend`)

- `app/services/ingestion.py` — CSV schema validation, timestamp/numeric
  parsing, dynamic equipment discovery, missing-value analysis, temporal-gap
  analysis. Nothing about equipment IDs, row counts, or dates is hard-coded.
- `app/services/preprocessing.py` — short missing-value runs are
  interpolated; large gaps are preserved/flagged rather than fabricated.
- `app/services/feature_engineering.py` — time-aware feature engineering:
  cyclic time features, per-equipment lag/rolling features computed strictly
  from *past* data (leakage-safe), equipment one-hot encoding.
- `app/ml/baseline.py` + `app/ml/xgboost_model.py` — Linear Regression
  baseline and the primary XGBoost regressor, predicting *expected* energy
  consumption (not a direct anomaly label).
- `app/services/training.py` — orchestrates ingestion → preprocessing →
  feature engineering → chronological train/val/test split → baseline →
  XGBoost → evaluation → held-out residual calibration → anomaly scoring →
  persistence grouping → SHAP → insights → persisted artifacts.
- `app/ml/residual_analysis.py` — per-equipment MAD-based robust z-score
  ("unusualness"), calibrated on held-out validation residuals only.
- `app/ml/persistence.py` — groups consecutive abnormal observations into
  abnormal periods; severity combines magnitude, persistence and recurrence.
- `app/services/explainability.py` — SHAP-based "model-associated
  contributing factors" (never a claimed physical fault).
- `app/services/insights.py` — turns a period + SHAP output into an
  evidence-based investigation writeup with an explicit disclaimer that no
  fault labels exist in the data.
- `app/services/prediction.py` — inference-only scoring of new observations
  using an already-trained model (no retraining).
- Full FastAPI surface: `/api/upload`, `/api/train/{id}`,
  `/api/train/status/{id}`, `/api/infer/{id}`, `/api/anomalies/{id}`,
  `/api/anomalies/{id}/{period_id}`, `/api/timeline/{id}`,
  `/api/overview/{id}`, `/api/equipment/{id}`,
  `/api/equipment/{id}/{equipment_id}`, `/api/health`.

Verified end-to-end by hand earlier in this project (see git history /
prior session notes): upload validation, training, injected persistent vs.
isolated anomalies flagged with correct relative severity, SHAP factors,
insights, inference-only scoring, and a full re-test against a second,
structurally-different dataset to confirm nothing is hard-coded.

## Frontend (`/frontend`)

Next.js 14 (App Router) + TypeScript + Tailwind, talking to the backend
purely over HTTP via `NEXT_PUBLIC_API_URL` (defaults to
`http://localhost:8000`).

Screens:

- **Upload** (`/upload`) — pick a CSV, see the ingestion validation report
  (equipment discovered, time range, missing values, temporal gaps), then
  trigger training and poll status until it completes, redirecting to
  Overview.
- **Overview** (`/overview`) — equipment count, abnormal-observation count,
  average energy, model R², plus priority abnormal periods and recent
  events, each linking into Investigation.
- **Equipment** (`/equipment`) — one card per equipment unit with status
  (normal / monitor / attention needed) and abnormal-period counts; drills
  into `/equipment/[id]` for an actual-vs-expected energy chart and that
  unit's abnormal periods.
- **Timeline** (`/timeline`) — all abnormal periods and individually
  flagged observations, filterable by equipment.
- **Investigation** (`/investigation/[id]`) — the evidence-based writeup for
  one abnormal period: summary, evidence bullets, an actual-vs-expected
  chart for that window, a SHAP contributing-factors chart, and the
  recommended-investigation checklist, always ending in the same
  no-fault-label disclaimer the backend produces.

The active dataset id is carried via a `?dataset=` query param and mirrored
into `localStorage` (`lib/useDataset.ts`) so navigating between screens
doesn't require re-selecting it.

### Note on this snapshot

This container has no outbound network access, so `npm install` /
`npm run build` could not be executed here to produce a build artifact or
catch type errors automatically. The code was written and manually
reviewed (import paths, JSX balance, prop/type shapes cross-checked
against the actual backend response schemas in `app/models/schemas.py` and
the JSON built in `app/services/training.py` / `app/ml/persistence.py` /
`app/services/insights.py`). Before running it for real:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # point at your backend if not localhost:8000
npm run dev      # or: npm run build && npm start
```

## Running the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then run the frontend against it as above. Use `data/sample_dataset.csv` or
`data/generate_synthetic_dataset.py` for a quick local test end-to-end:
upload → train → overview → equipment → timeline → investigation.
