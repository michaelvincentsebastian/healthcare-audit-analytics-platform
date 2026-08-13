FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend (main.py) DAN frontend statis (dashboard) ikut ke-copy dalam satu
# image -- FastAPI serve keduanya (lihat app.mount("/", StaticFiles(...)) di
# backend/main.py), supaya tidak perlu container/nginx terpisah untuk
# dashboard yang masih sederhana ini.
COPY backend/ backend/
COPY frontend/ frontend/

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
