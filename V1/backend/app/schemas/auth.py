"""
Schemi Pydantic per autenticazione e gestione utenti (Fase 4 — DL-ARCH-016).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    ruolo: str                # produzione | magazzino | logistica | admin


class UtenteCreateRequest(BaseModel):
    username: str
    password: str
    ruolo: str


class UtentePatchRequest(BaseModel):
    password: Optional[str] = None
    ruolo: Optional[str] = None
    attivo: Optional[bool] = None


class UtenteResponse(BaseModel):
    id: str
    username: str
    ruolo: str
    attivo: bool
    created_at: datetime

    class Config:
        from_attributes = True
