"""
Router autenticazione e gestione utenti (DL-ARCH-016).

POST /api/auth/login           — {username, password} → JWT token
GET  /api/auth/me              — info utente corrente (richiede JWT)
POST /api/auth/utenti          — crea utente (solo admin)
GET  /api/auth/utenti          — lista utenti (solo admin)
PATCH /api/auth/utenti/{id}    — aggiorna utente (solo admin)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UtenteCreateRequest,
    UtentePatchRequest,
    UtenteResponse,
)
from app.services.auth import AuthError, login, crea_utente, get_utenti, aggiorna_utente

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def do_login(body: LoginRequest, session: Session = Depends(get_db)):
    """Autentica l'utente e ritorna il JWT token (durata configurabile via JWT_EXPIRE_HOURS)."""
    try:
        return login(session, body.username, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ---------------------------------------------------------------------------
# Info utente corrente
# ---------------------------------------------------------------------------

@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """Ritorna username e ruolo dell'utente autenticato."""
    return {
        "id": user.get("sub"),
        "username": user.get("username"),
        "ruolo": user.get("ruolo"),
    }


# ---------------------------------------------------------------------------
# Gestione utenti (solo admin)
# ---------------------------------------------------------------------------

@router.post("/utenti", response_model=UtenteResponse, status_code=201)
def create_utente(
    body: UtenteCreateRequest,
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Crea un nuovo utente (solo admin)."""
    try:
        return crea_utente(session, body.username, body.password, body.ruolo)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/utenti", response_model=list[UtenteResponse])
def list_utenti(
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Lista tutti gli utenti (solo admin)."""
    return get_utenti(session)


@router.patch("/utenti/{utente_id}", response_model=UtenteResponse)
def patch_utente(
    utente_id: str,
    body: UtentePatchRequest,
    session: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Aggiorna password, ruolo o stato attivo di un utente (solo admin)."""
    try:
        return aggiorna_utente(session, utente_id, body.model_dump(exclude_none=True))
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
