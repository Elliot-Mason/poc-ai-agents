# Blackcard

Blackcard contains two payroll-themed variants.

- `safe/` is a fixed-response FastAPI service and does not use Bedrock.
- `unsafe/` is Bedrock-backed and uses an MCP tool server.

## Safe Variant

```bash
cd blackcard/safe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Unsafe Variant

```bash
cd blackcard/unsafe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python init_db.py
uvicorn app:app --reload
```

Set `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL_ID`, and `AWS_REGION` in `.env` before starting the unsafe service.
