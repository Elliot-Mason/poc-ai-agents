# Agent Demo Handoff

This repository contains three agent demo projects with safe and unsafe variants:

- `aimortgage/` - mortgage rate and quote assistant.
- `creditcardbot/` - credit card comparison and application assistant.
- `blackcard/` - payroll-themed demo; `safe` is a fixed-response service and `unsafe` is Bedrock-backed.

The `poc/` and `prompts/` folders are intentionally excluded from the GitHub handoff.

## Bedrock Configuration

For Bedrock-backed variants, copy the local template and fill in your token:

```bash
cp .env.example <project>/<variant>/.env
```

Required values:

```env
AWS_BEARER_TOKEN_BEDROCK=replace-me
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
AWS_REGION=ap-southeast-2
```

The model name is the main value most users should change. The apps default to `anthropic.claude-sonnet-4-5-20250929-v1:0` and `ap-southeast-2` when the variables are omitted.

## Run A Variant

From a variant directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Initialize the database when that variant has an initializer:

```bash
python init_db.py
```

For `creditcardbot` variants, the initializer lives under `db/`:

```bash
python db/init_db.py
```

Start FastAPI:

```bash
uvicorn app:app --reload
```

For `creditcardbot/unsafe`, start the backend from `creditcardbot/unsafe`:

```bash
uvicorn backend.app:app --reload
```

## Variant Notes

- `aimortgage/safe` and `aimortgage/unsafe` expose `/api/chat`, `/api/rates`, and `/api/quotes`.
- `creditcardbot/safe` exposes `/chat` and `/applications`.
- `creditcardbot/unsafe` uses `boto3` and also supports the legacy `LLM_MODEL` environment variable, but `BEDROCK_MODEL_ID` takes precedence.
- `blackcard/safe` does not require Bedrock; run it with `uvicorn main:app --reload`.
- `blackcard/unsafe` requires Bedrock and exposes `/api/chat` plus `/api/logs`.

## GitHub Hygiene

Do not commit real `.env` files, credentials, virtual environments, logs, prompt/output captures, generated SQLite databases, pycache files, or nested `.git` folders. The root `.gitignore` is set up to keep these local-only artifacts out of the handoff.
