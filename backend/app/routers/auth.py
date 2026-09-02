"""Routes d'authentification."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import security
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginPayload(BaseModel):
    password: str


@router.get("/status")
def status():
    """Etat de la protection (utilise par le front pour afficher login / blocage)."""
    return {
        "auth_active": security.auth_active(),
        "locked": security.is_locked(),
    }


@router.post("/login")
def login(payload: LoginPayload):
    if security.is_locked():
        raise HTTPException(423, "Application bloquée. Remettez APP_ENABLED=true dans .env puis redémarrez.")
    if not security.auth_active():
        # Aucune protection : on renvoie quand meme un jeton neutre.
        return {"token": "no-auth"}
    if payload.password == settings.app_password:
        security.reset_attempts()
        return {"token": security.expected_token()}
    n = security.register_failed_attempt()
    if security.is_locked():
        raise HTTPException(423, "Trop de tentatives : application bloquée. "
                                 "Remettez APP_ENABLED=true dans .env puis redémarrez.")
    raise HTTPException(401, f"Mot de passe incorrect. Tentatives restantes : {security.attempts_left()}.")
