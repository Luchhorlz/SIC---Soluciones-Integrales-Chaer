# SIC API

API interna FastAPI. En desarrollo local:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn sic_api.main:app --app-dir src --reload
```
