from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    nome: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    jogador_id: int
    nome: str
    is_admin: bool


# ── Jogadores ─────────────────────────────────────────────────────────────────

class JogadorCreate(BaseModel):
    nome: str
    senha: str


class RedefinirSenhaRequest(BaseModel):
    nova_senha: str


class JogadorOut(BaseModel):
    id: int
    nome: str
    is_admin: bool
    total_palpites: int = 0

    model_config = {"from_attributes": True}


# ── Palpites ──────────────────────────────────────────────────────────────────

class PalpiteUpsert(BaseModel):
    gols_casa: Optional[int] = Field(None, ge=0, le=20)
    gols_fora: Optional[int] = Field(None, ge=0, le=20)
    avanca: Optional[Literal["casa", "fora"]] = None


class PalpiteOut(BaseModel):
    jogo_id: str
    gols_casa: Optional[int]
    gols_fora: Optional[int]
    avanca: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Resultados ────────────────────────────────────────────────────────────────

class ResultadoUpsert(BaseModel):
    gols_casa: int = Field(ge=0, le=20)
    gols_fora: int = Field(ge=0, le=20)
    avanca: Optional[Literal["casa", "fora"]] = None


class ResultadoOut(BaseModel):
    jogo_id: str
    gols_casa: int
    gols_fora: int
    avanca: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Bônus ─────────────────────────────────────────────────────────────────────

class BonusUpsert(BaseModel):
    campeao: Optional[str] = None
    artilheiro: Optional[str] = None


class BonusOut(BaseModel):
    campeao: Optional[str]
    artilheiro: Optional[str]

    model_config = {"from_attributes": True}


# ── Oficiais ──────────────────────────────────────────────────────────────────

class OficiaisUpsert(BaseModel):
    campeao: Optional[str] = None
    artilheiro: Optional[str] = None


class OficiaisOut(BaseModel):
    campeao: Optional[str]
    artilheiro: Optional[str]

    model_config = {"from_attributes": True}


# ── Ranking ───────────────────────────────────────────────────────────────────

class RankingEntry(BaseModel):
    posicao: int
    jogador_id: int
    nome: str
    total: int
    placar_exato: int       # 1° critério de desempate
    resultado_correto: int  # 2° critério de desempate
    acertou_artilheiro: bool  # 3° critério de desempate
    acertou_campeao: bool     # 4° critério de desempate
    artilheiro_palpite: Optional[str] = None
    campeao_palpite: Optional[str] = None
    vencedor_mais_gols: int
    so_vencedor: int
    gols_de_um_time: int


# ── Mata-mata: times reais ────────────────────────────────────────────────────

class JogoTimesUpsert(BaseModel):
    casa: str
    fora: str


# ── Jogos ─────────────────────────────────────────────────────────────────────

class JogoOut(BaseModel):
    id: str
    fase: str
    multiplicador: int
    eh_mata_mata: bool
    casa: str
    fora: str
    data: str
    horario: str


# ── Web Push ──────────────────────────────────────────────────────────────────

class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: Optional[dict] = None
    expirationTime: Optional[str] = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str
