# CreditCardBot

CreditCardBot contains safe and unsafe credit card assistant variants.

- `safe/` uses the shared MCP agent pattern with `llm/bedrock_adapter.py`.
- `unsafe/` uses a direct `boto3` Bedrock backend under `backend/app.py`.

## Bedrock Setup

From either variant directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `.env`:

```env
AWS_BEARER_TOKEN_BEDROCK=replace-me
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
AWS_REGION=ap-southeast-2
```

`creditcardbot/unsafe` also supports the older `LLM_MODEL` variable, but `BEDROCK_MODEL_ID` takes precedence.

## Safe Variant

```bash
cd creditcardbot/safe
python db/init_db.py
uvicorn app:app --reload
```

Open <http://localhost:8000>.

## Unsafe Variant

```bash
cd creditcardbot/unsafe
python db/init_db.py
uvicorn backend.app:app --reload
```

Open <http://localhost:8000>.
