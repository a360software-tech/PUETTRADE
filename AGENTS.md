# AGENTS.md

## Project Overview

PUETTRADE is a trading platform in progress built around the IG Labs API.

- Backend: FastAPI service that authenticates against IG, exposes normalized endpoints, and acts as the only integration boundary with IG Labs.
- Frontend: Next.js 16 App Router application that consumes the backend and renders trading-oriented UI, starting with market discovery and candlestick charts.
- Provider model: IG Labs is an external system. Do not couple frontend code directly to IG response formats when a backend-normalized contract exists.

Current active backend domains:

- `authentication`
- `market_discovery`
- `market_data`

Current frontend focus:

- `(dashboard)` market exploration route
- normalized candle consumption from backend
- chart rendering with `lightweight-charts`

## Development Setup

### Backend

Environment:

- Python should be created with `python3`, not `python`
- The repo uses a local virtual environment in `backend/.venv`

Install:

```bash
cd backend
python3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Backend env:

- Copy `backend/.env.example` to `backend/.env`
- Fill at minimum:
  - `IG_API_KEY`
  - `SECRET_KEY`

Run backend:

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
```

### Frontend

Install:

```bash
cd frontend
pnpm install
```

Optional env:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Run frontend:

```bash
cd frontend
pnpm dev
```

## Build, Test, and Validation Commands

### Backend commands

Run tests:

```bash
cd backend
.venv\Scripts\python.exe -m pytest
```

Compile check:

```bash
cd backend
.venv\Scripts\python.exe -m compileall src
```

Useful local URLs:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`

### Frontend commands

Lint:

```bash
cd frontend
pnpm lint
```

Build:

```bash
cd frontend
pnpm build
```

Useful local URL:

- `http://localhost:3000/markets/CS.D.EURUSD.CFD.IP`

## Project Structure

Top-level:

```text
backend/
frontend/
AGENTS.md
```

Backend structure:

```text
backend/
  src/
    authentication/
    market_discovery/
    market_data/
    integrations/ig/
    shared/
  tests/
```

Frontend structure:

```text
frontend/
  app/
    (dashboard)/
      markets/[epic]/
        _components/
        _hooks/
    (auth)/        # reserved for future auth UI
  components/
    ui/
  lib/
  hooks/
  types/
  utils/
```

## Code Style and Conventions

### General

- Keep changes small, explicit, and consistent with the existing structure.
- Prefer improving existing modules over introducing parallel patterns.
- Use ASCII by default unless a file already requires other characters.
- Do not add comments unless they clarify non-obvious business or integration logic.

### Backend conventions

- Use Python type hints everywhere.
- Use FastAPI routers per bounded context.
- Keep request/response contracts in `application/dto.py`.
- Keep integration code isolated under `integrations/ig/`.
- Prefer normalized backend contracts for frontend consumption.
- Raise application-specific exceptions from `shared/errors/base.py` instead of returning ad-hoc errors.
- Do not bypass the backend and do not expose IG-specific payloads to the frontend unless there is a strong reason.

Current patterns to follow:

- Routers in `presentation/router.py`
- Service layer in `application/service.py`
- Shared error handling in `backend/src/main.py`

### Frontend conventions

- Use App Router patterns from Next.js 16.
- Default to Server Components; use `"use client"` only where interactivity or browser APIs are required.
- Route-local UI belongs under route-scoped `_components/`, `_hooks/`, and later `_actions/`.
- Shared UI goes to `components/ui/`.
- Shared API clients go to `lib/`.
- Shared types go to `types/`.
- Use the `@/` alias defined in `frontend/tsconfig.json`.
- Keep trading UI intentional, not generic starter UI.

Frontend-specific current rule:

- Authentication pages must live under `app/(auth)/...`, not inside `(dashboard)`.

## Active API Contracts

Backend routes currently exposed:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/session`
- `GET /api/v1/auth/status`
- `GET /api/v1/markets/categories`
- `GET /api/v1/markets/categories/{category_id}/instruments`
- `GET /api/v1/markets/search?q=...`
- `GET /api/v1/markets/{epic}`
- `GET /api/v1/market-data/{epic}/candles`

For charts, prefer the normalized candle contract from `backend/src/market_data/application/dto.py`:

```json
{
  "epic": "CS.D.EURUSD.CFD.IP",
  "resolution": "MINUTE",
  "candles": [
    {
      "time": "2026-03-14T03:00:00",
      "open": 1.0912,
      "high": 1.0918,
      "low": 1.0909,
      "close": 1.0915,
      "volume": 123.0
    }
  ],
  "allowance_remaining": 9998,
  "allowance_total": 10000
}
```

## Testing Requirements

- Backend changes should include or update pytest coverage when behavior changes.
- Frontend changes should pass `pnpm lint` and `pnpm build`.
- If you change a backend contract, update the frontend client and any related types in the same task when possible.
- Validate the main route after UI changes: `/markets/[epic]`.

Minimum expected validation before considering work complete:

- Backend: `pytest`
- Frontend: `pnpm lint` and `pnpm build`

## Workflow Rules

- Prefer implementing one bounded context at a time.
- Keep the frontend consuming the backend, not IG directly.
- If a feature is not ready end-to-end, prefer a controlled fallback over breaking the UI.
- Current approved fallback: the frontend candles view may use preview/mock candles when the backend has no active session.
- Preserve the existing naming split between internal product language and IG integration language.

When adding new functionality:

1. Add or extend backend domain module
2. Expose normalized endpoint
3. Add frontend client in `lib/`
4. Add route-local UI under `app/(dashboard)` or `app/(auth)`
5. Validate backend and frontend

## Security and Constraints

- Never commit secrets, tokens, credentials, or real account information.
- Environment variables must come from `.env`, `.env.local`, or equivalent local files.
- Do not hardcode IG credentials or session tokens.
- Do not expose IG API keys to the frontend.
- Do not make the frontend call IG directly.
- Do not remove auth/session checks from backend endpoints that require IG access.
- The backend currently stores session state in memory only; do not assume multi-user or production-grade session persistence yet.

## Domain Concepts

- `epic`: IG market identifier used throughout backend and frontend routing.
- `candle`: normalized OHLCV item used by the frontend chart.
- `market discovery`: categories, search, and market detail exploration.
- `market data`: historical candles and later snapshots/streaming.
- `preview fallback`: frontend mock-candle mode used when backend access fails or no active backend session exists.
- `IG Labs`: external trading provider and authoritative source of market/trading data.

## Agent Guidance

If you are an AI coding agent working in this repo:

- Read this file first.
- Prefer official docs and current framework APIs.
- Respect the current architecture before introducing abstractions.
- Do not reintroduce removed placeholder modules unless they are being implemented for real.
- Keep route groups semantically correct: `(dashboard)` for trading UI, `(auth)` for future authentication UI.
- When in doubt, keep backend contracts clean and frontend components focused.
