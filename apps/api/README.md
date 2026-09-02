# CloudOps API

FastAPI service for the CloudOps console. Phase 2 returns realistic mock data from
provider adapters. AWS and Alibaba credentials are not used.

```bash
cd apps/api
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

API: [http://127.0.0.1:8000/api/v1](http://127.0.0.1:8000/api/v1)  
Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Secret values, tokens, private keys, and PEM material are never returned.
