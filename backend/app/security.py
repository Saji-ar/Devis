"""Securite simple : un mot de passe partage + blocage apres trop d'echecs.

- Le mot de passe est en clair dans .env (APP_PASSWORD).
- Apres connexion reussie, le serveur renvoie un jeton deterministe (sha256 du mot de passe)
  que le navigateur garde en localStorage : l'utilisateur ne retape pas le mot de passe.
- Apres plus de MAX_LOGIN_ATTEMPTS echecs, l'appli se bloque : APP_ENABLED passe a false
  dans .env. Pour relancer, remettre manuellement APP_ENABLED=true dans .env puis redemarrer.
"""
import hashlib
import re
from pathlib import Path

from fastapi import Header, HTTPException

from .config import settings

# Compteur d'echecs en memoire (remis a zero au redemarrage ; le blocage, lui, est persiste).
_failed_attempts = 0

_ENV_PATH = Path(".env")


def auth_active() -> bool:
    """La protection par mot de passe est active si un mot de passe est defini."""
    return bool(settings.app_password)


def expected_token() -> str:
    return hashlib.sha256(("devis:" + settings.app_password).encode("utf-8")).hexdigest()


def is_locked() -> bool:
    return not settings.app_enabled


def _persist_disabled() -> None:
    """Ecrit APP_ENABLED=false dans .env (blocage persistant)."""
    settings.app_enabled = False
    if _ENV_PATH.exists():
        txt = _ENV_PATH.read_text(encoding="utf-8")
        if re.search(r"(?mi)^APP_ENABLED=", txt):
            txt = re.sub(r"(?mi)^APP_ENABLED=.*$", "APP_ENABLED=false", txt)
        else:
            txt = txt.rstrip("\n") + "\nAPP_ENABLED=false\n"
        _ENV_PATH.write_text(txt, encoding="utf-8")


def register_failed_attempt() -> int:
    """Enregistre un echec. Bloque l'appli si on depasse le maximum. Renvoie le nb d'echecs."""
    global _failed_attempts
    _failed_attempts += 1
    if _failed_attempts > settings.max_login_attempts:
        _persist_disabled()
    return _failed_attempts


def reset_attempts() -> None:
    global _failed_attempts
    _failed_attempts = 0


def attempts_left() -> int:
    return max(0, settings.max_login_attempts - _failed_attempts)


def require_auth(x_auth_token: str = Header(default="")) -> None:
    """Dependance FastAPI a placer sur les routes protegees."""
    if is_locked():
        raise HTTPException(status_code=423, detail="Application bloquée (trop de tentatives). "
                                                    "Remettez APP_ENABLED=true dans .env puis redémarrez.")
    if not auth_active():
        return  # aucune protection configuree
    if x_auth_token != expected_token():
        raise HTTPException(status_code=401, detail="Non authentifié")
