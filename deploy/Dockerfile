# Image unique servant l'API FastAPI + le front React compile.
# Compatible Raspberry Pi (arm64) grace aux images officielles multi-arch.

# --- Etape 1 : build du front React ---
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Etape 2 : runtime Python + LibreOffice ---
FROM python:3.12-slim
# LibreOffice Calc pour la conversion xlsx -> pdf (mise en page preservee).
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-calc fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# Front compile place la ou main.py le cherche (../frontend/dist).
COPY --from=frontend /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
