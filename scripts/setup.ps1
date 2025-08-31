$env:RUN_MODE="local"
uvicorn api.main:app --reload --port 9000
