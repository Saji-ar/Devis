"""Point d'entree FastAPI de l'appli Devis."""
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .security import require_auth
from .routers import auth, clients, devis

app = FastAPI(title="Devis Traiteur", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes ouvertes (auth) et routes protegees par mot de passe.
app.include_router(auth.router)
app.include_router(clients.router, dependencies=[Depends(require_auth)])
app.include_router(devis.router, dependencies=[Depends(require_auth)])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "devis_dir": str(settings.devis_dir)}


# Sert le front React compile (frontend/dist) s'il existe. Un seul process sert l'API +
# l'interface. Un fallback renvoie index.html pour les routes cote client (SPA).
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
