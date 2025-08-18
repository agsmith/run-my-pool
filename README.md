# PFM UI - Python Only (FastAPI + Jinja2)

## How to Run

1. Install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the server:
   ```
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Open your browser to [http://localhost:8000/login](http://localhost:8000/login)

- Set environment variables for `MONGO_URI`, `BASIC_AUTH_USER`, and `BASIC_AUTH_PASS` as needed.
- UI is fully Python-based, no frontend build step required.
- Inspired by the original docs UI, but now all CRUD and auth is in Python.
# run-my-pool
