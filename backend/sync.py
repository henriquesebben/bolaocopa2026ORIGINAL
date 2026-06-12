"""
Sincronizador automático de resultados via API-Football (RapidAPI).

Estratégia de chamadas para respeitar o limite gratuito (100/dia):
  - Agenda:  1 chamada a cada 4h → verifica mudanças de horário/adiamentos
  - Janela:  1 chamada a cada SYNC_INTERVAL_MINS durante jogos ativos
  - Fora de janela: zero chamadas extras

Uma única chamada por ciclo retorna TODOS os jogos do dia filtrados pela Copa.
"""

import json
import logging
import math
import os
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import SessionLocal
from . import models
from .jogos import JOGOS

logger = logging.getLogger(__name__)

RAPIDAPI_KEY         = os.getenv("RAPIDAPI_KEY", "")
API_PROVIDER         = os.getenv("API_PROVIDER", "api-football").lower()  # 'api-football' ou 'allsportsapi2'
WC2026_LEAGUE_ID     = int(os.getenv("WC2026_LEAGUE_ID", "1"))
SEASON               = 2026
SYNC_INTERVAL_MINS   = int(os.getenv("SYNC_INTERVAL_MINS", "30"))
MAX_DAILY_API_CALLS  = int(os.getenv("MAX_DAILY_API_CALLS", "100"))

# ── Mapeamento nome API (inglês) → nome interno (português) ──────────────────

TEAM_MAP: dict[str, str] = {
    "Mexico": "México",
    "South Africa": "África do Sul",
    "South Korea": "Coreia do Sul",
    "Czech Republic": "Tchéquia",
    "Czechia": "Tchéquia",
    "Canada": "Canadá",
    "Bosnia": "Bósnia-Herzegovina",
    "Bosnia and Herzegovina": "Bósnia-Herzegovina",
    "Bosnia & Herzegovina": "Bósnia-Herzegovina",
    "Qatar": "Catar",
    "Switzerland": "Suíça",
    "Brazil": "Brasil",
    "Morocco": "Marrocos",
    "Haiti": "Haiti",
    "Scotland": "Escócia",
    "United States": "Estados Unidos",
    "USA": "Estados Unidos",
    "Paraguay": "Paraguai",
    "Australia": "Austrália",
    "Turkey": "Turquia",
    "Türkiye": "Turquia",
    "Germany": "Alemanha",
    "Ecuador": "Equador",
    "Curacao": "Curaçao",
    "Curaçao": "Curaçao",
    "Ivory Coast": "Costa do Marfim",
    "Côte d'Ivoire": "Costa do Marfim",
    "Netherlands": "Holanda",
    "Tunisia": "Tunísia",
    "Sweden": "Suécia",
    "Iran": "Irã",
    "Belgium": "Bélgica",
    "New Zealand": "Nova Zelândia",
    "Japan": "Japão",
    "Panama": "Panamá",
    "Spain": "Espanha",
    "Uruguay": "Uruguai",
    "Algeria": "Argélia",
    "Jordan": "Jordânia",
    "France": "França",
    "Senegal": "Senegal",
    "Iraq": "Iraque",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Austria": "Áustria",
    "Cape Verde": "Cabo Verde",
    "Costa Rica": "Costa Rica",
    "Portugal": "Portugal",
    "DR Congo": "RD Congo",
    "Congo DR": "RD Congo",
    "Uzbekistan": "Uzbequistão",
    "Colombia": "Colômbia",
    "England": "Inglaterra",
    "Croatia": "Croácia",
    "Ghana": "Gana",
    "Nigeria": "Nigéria",
    "Egypt": "Egito",
    "Saudi Arabia": "Arábia Saudita",
}

# ── Lookup (time_casa_norm, time_fora_norm) → jogo_id ────────────────────────

def _norm(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _pt(api_name: str) -> str:
    return TEAM_MAP.get(api_name, api_name)


# Mapeamento estático para a fase de grupos (construído uma vez no boot)
_PAIR_GRUPOS: dict[tuple[str, str], str] = {
    (_norm(j["casa"]), _norm(j["fora"])): j["id"]
    for j in JOGOS
    if j["fase"].startswith("Grupo")
}


_pair_to_jogo_cache: tuple[dict[tuple[str, str], str], float] | None = None
_PAIR_CACHE_TTL = 300  # segundos


def _construir_pair_to_jogo() -> dict[tuple[str, str], str]:
    """Mescla grupos (estático) + nomes reais do mata-mata. Resultado cacheado por 5 min."""
    global _pair_to_jogo_cache
    import time as _time
    now = _time.monotonic()
    if _pair_to_jogo_cache is not None:
        cached, ts = _pair_to_jogo_cache
        if now - ts < _PAIR_CACHE_TTL:
            return cached
    result = dict(_PAIR_GRUPOS)
    db = SessionLocal()
    try:
        for o in db.query(models.JogoNomeReal).all():
            result[(_norm(o.casa_real), _norm(o.fora_real))] = o.jogo_id
    except Exception:
        pass
    finally:
        db.close()
    _pair_to_jogo_cache = (result, now)
    return result


# ── Estado em memória ─────────────────────────────────────────────────────────

_janelas: list[tuple[datetime, datetime]] = []   # janelas de jogo hoje
_ultimo_fetch: Optional[datetime] = None
_ultimo_sync_log: str = "Ainda não sincronizado"

# Contador diário de chamadas à API (proteção contra estouro do limite gratuito)
_calls_hoje: int = 0
_data_contagem: str = ""   # YYYY-MM-DD UTC


def _registrar_chamada() -> bool:
    """Incrementa o contador diário. Retorna False se o limite foi atingido."""
    global _calls_hoje, _data_contagem
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if hoje != _data_contagem:
        _calls_hoje = 0
        _data_contagem = hoje
    if _calls_hoje >= MAX_DAILY_API_CALLS:
        logger.warning(
            f"[sync] Limite diário de {MAX_DAILY_API_CALLS} chamadas atingido "
            f"— sync pausado até meia-noite UTC"
        )
        return False
    _calls_hoje += 1
    return True

# Chaves VAPID — preenchidas por iniciar_scheduler()
_vapid_private: str = ""
_vapid_public:  str = ""
_vapid_subject: str = ""


def status_sync() -> dict:
    return {
        "ultimo_fetch": _ultimo_fetch.isoformat() if _ultimo_fetch else None,
        "janelas_hoje": len(_janelas),
        "em_janela": _em_janela(),
        "log": _ultimo_sync_log,
        "chamadas_hoje": _calls_hoje,
        "limite_diario": MAX_DAILY_API_CALLS,
    }


# ── Chamada à API ─────────────────────────────────────────────────────────────

async def _fetch_api_football() -> list:
    """Busca jogos da API-Football (antiga, se ainda estiver configurada)."""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://api-football-v1.p.rapidapi.com/v3/fixtures",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
                },
                params={"league": WC2026_LEAGUE_ID, "season": SEASON, "date": hoje},
            )
            r.raise_for_status()
            return r.json().get("response", [])
    except Exception as e:
        logger.error(f"[sync] Erro na API-Football: {e}")
        return []


async def _fetch_allsportsapi2() -> list:
    """
    Busca jogos da AllSportsApi2 (novo provider).
    Converte para o formato esperado pelo código (compatível com API-Football).
    """
    hoje = datetime.now(timezone.utc)
    day, month, year = hoje.day, hoje.month, hoje.year
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            # Busca todos os jogos do dia
            r = await c.get(
                f"https://allsportsapi2.p.rapidapi.com/api/matches/{day}/{month}/{year}",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com",
                },
            )
            r.raise_for_status()
            data = r.json()
            
            # AllSportsApi2 retorna um objeto genérico; extrair a lista de matches
            matches = data.get("events", data.get("response", []))
            if not isinstance(matches, list):
                return []
            
            # Filtrar apenas jogos da Copa do Mundo e converter para o formato API-Football
            converted = []
            for match in matches:
                # Verificar se é da Copa do Mundo (tournament contém "world" ou "2026")
                tournament = match.get("tournament", {}).get("name", "").lower()
                if "world" not in tournament and "fifa" not in tournament and "2026" not in tournament:
                    continue
                
                # Converter para o formato esperado
                ts = match.get("startTimestamp") or 0

                # status pode ser dict {"type": "finished", ...} ou string
                raw_status = match.get("status", "")
                if isinstance(raw_status, dict):
                    raw_status = raw_status.get("type", "")

                # score pode ser dict {"current": 2, ...} ou int
                home_score = match.get("homeScore")
                away_score = match.get("awayScore")
                if isinstance(home_score, dict):
                    home_score = home_score.get("current")
                if isinstance(away_score, dict):
                    away_score = away_score.get("current")

                converted.append({
                    "fixture": {
                        "id": match.get("id"),
                        "date": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                        "status": {
                            "short": _converter_status(raw_status)
                        }
                    },
                    "teams": {
                        "home": {"name": match.get("homeTeam", {}).get("name", "")},
                        "away": {"name": match.get("awayTeam", {}).get("name", "")}
                    },
                    "goals": {
                        "home": home_score,
                        "away": away_score
                    }
                })
            
            return converted
    except Exception as e:
        logger.error(f"[sync] Erro na AllSportsApi2: {e}")
        return []


def _converter_status(status_str: str) -> str:
    """Converte status da AllSportsApi2 para o formato da API-Football."""
    status_map = {
        "finished": "FT",
        "aet": "AET",
        "penalties": "PEN",
        "live": "1H",
        "scheduled": "NS",
    }
    return status_map.get(status_str.lower(), "NS")


async def _fetch_hoje() -> list:
    if not RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY não configurado — sync desativado")
        return []
    if not _registrar_chamada():
        return []  # teto diário atingido
    
    if API_PROVIDER == "allsportsapi2":
        return await _fetch_allsportsapi2()
    else:
        return await _fetch_api_football()


# ── Janelas de jogo ───────────────────────────────────────────────────────────

def _atualizar_janelas(fixtures: list) -> None:
    global _janelas, _ultimo_fetch
    _janelas = []
    for f in fixtures:
        kickoff = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
        _janelas.append((
            kickoff - timedelta(minutes=10),
            kickoff + timedelta(minutes=130),  # 90min jogo + 30min gordo + prorrogação
        ))
    _ultimo_fetch = datetime.now(timezone.utc)
    logger.info(f"[sync] Agenda: {len(_janelas)} jogo(s) hoje")


def _em_janela() -> bool:
    now = datetime.now(timezone.utc)
    return any(s <= now <= e for s, e in _janelas)


# ── Processamento dos resultados ──────────────────────────────────────────────

async def _processar(fixtures: list) -> int:
    global _ultimo_sync_log
    atualizados = 0
    pair_to_jogo = _construir_pair_to_jogo()
    db = SessionLocal()
    try:
        for f in fixtures:
            status = f["fixture"]["status"]["short"]
            if status not in ("FT", "AET", "PEN"):
                continue  # jogo não finalizado

            gols_casa = f["goals"]["home"]
            gols_fora = f["goals"]["away"]
            if gols_casa is None or gols_fora is None:
                continue

            home_pt = _pt(f["teams"]["home"]["name"])
            away_pt = _pt(f["teams"]["away"]["name"])
            jogo_id = pair_to_jogo.get((_norm(home_pt), _norm(away_pt)))
            if not jogo_id:
                continue

            avanca = None
            if gols_casa == gols_fora:
                home_won = f["teams"]["home"].get("winner")
                away_won = f["teams"]["away"].get("winner")
                if home_won is True:
                    avanca = "casa"
                elif away_won is True:
                    avanca = "fora"

            existente = db.query(models.Resultado).filter(
                models.Resultado.jogo_id == jogo_id
            ).first()

            if existente:
                if existente.gols_casa == gols_casa and existente.gols_fora == gols_fora and existente.avanca == avanca:
                    continue
                existente.gols_casa = gols_casa
                existente.gols_fora = gols_fora
                if avanca is not None:
                    existente.avanca = avanca
            else:
                db.add(models.Resultado(
                    jogo_id=jogo_id, gols_casa=gols_casa, gols_fora=gols_fora, avanca=avanca
                ))
            atualizados += 1

        if atualizados:
            db.commit()
    finally:
        db.close()

    now_str = datetime.now(timezone.utc).strftime("%d/%m %H:%M UTC")
    _ultimo_sync_log = f"{now_str} — {atualizados} resultado(s) atualizado(s)"
    if atualizados:
        logger.info(f"[sync] {atualizados} resultado(s) salvo(s)")
    return atualizados


def _deve_sincronizar() -> tuple[bool, str]:
    """Retorna (deve_sincronizar, motivo). Pula durante madrugada sem jogos ativos."""
    now = datetime.now(timezone.utc)
    # UTC 5–9 = Brasília 2–6h: evita chamadas desnecessárias à API
    if 5 <= now.hour <= 9 and not _em_janela():
        return False, "madrugada (sem jogos)"
    return True, ""


# ── Job principal (roda a cada SYNC_INTERVAL_MINS) ───────────────────────────

async def job_principal():
    global _ultimo_fetch
    now = datetime.now(timezone.utc)
    agenda_expirada = _ultimo_fetch is None or (now - _ultimo_fetch).total_seconds() > 4 * 3600

    # Verifica condições inteligentes antes de sincronizar
    deve_sync, motivo = _deve_sincronizar()
    if not deve_sync and not agenda_expirada and not _em_janela():
        logger.debug(f"[sync] Pulando sincronização: {motivo}")
        return

    if not agenda_expirada and not _em_janela():
        return  # fora de janela e agenda recente → zero chamadas à API

    fixtures = await _fetch_hoje()   # UMA chamada serve pra tudo
    if agenda_expirada and fixtures:
        _atualizar_janelas(fixtures)
    if fixtures:
        await _processar(fixtures)


# ── Sync manual (chamado pelo endpoint /api/admin/sync) ───────────────────────

async def sync_manual() -> dict:
    global _ultimo_fetch
    _ultimo_fetch = None  # força refresh da agenda também
    fixtures = await _fetch_hoje()
    if fixtures:
        _atualizar_janelas(fixtures)
        atualizados = await _processar(fixtures)
    else:
        atualizados = 0
    return {"atualizados": atualizados, "jogos_hoje": len(_janelas), "log": _ultimo_sync_log}


# ── Notificações push ─────────────────────────────────────────────────────────

def _inicio_utc(jogo: dict) -> datetime:
    BRT = timezone(timedelta(hours=-3))
    ano, mes, dia = map(int, jogo["data"].split("-"))
    hora, minuto = map(int, jogo["horario"].split(":"))
    return datetime(ano, mes, dia, hora, minuto, tzinfo=BRT).astimezone(timezone.utc)


async def job_notificacoes():
    """Dispara push 2h antes de cada jogo para todos os inscritos."""
    if not _vapid_private:
        return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return

    now = datetime.now(timezone.utc)
    alvo_min = now + timedelta(hours=1, minutes=55)
    alvo_max = now + timedelta(hours=2, minutes=5)

    db = SessionLocal()
    try:
        subs = db.query(models.PushSubscription).all()
        if not subs:
            return

        for jogo in JOGOS:
            inicio = _inicio_utc(jogo)
            if not (alvo_min <= inicio <= alvo_max):
                continue

            # Verifica no banco se já enviamos (sobrevive a reinícios)
            ja_enviada = db.query(models.NotificacaoEnviada).filter(
                models.NotificacaoEnviada.jogo_id == jogo["id"]
            ).first()
            if ja_enviada:
                continue

            hora_brt = jogo["horario"]
            titulo = f"⚽ {jogo['casa']} × {jogo['fora']}"
            corpo  = f"Daqui a 2 horas — {hora_brt}h (Brasília). Faça seu palpite!"

            enviados = 0
            mortos   = []
            for sub in subs:
                try:
                    webpush(
                        subscription_info=json.loads(sub.subscription_json),
                        data=json.dumps({"title": titulo, "body": corpo}),
                        vapid_private_key=_vapid_private,
                        vapid_claims={"sub": _vapid_subject},
                    )
                    enviados += 1
                except WebPushException as e:
                    if e.response and e.response.status_code in (404, 410):
                        mortos.append(sub.id)
                except Exception:
                    pass

            if mortos:
                for sid in mortos:
                    db.query(models.PushSubscription).filter(
                        models.PushSubscription.id == sid
                    ).delete()
                db.commit()

            # Persiste no banco para não reenviar após reinício
            db.add(models.NotificacaoEnviada(jogo_id=jogo["id"]))
            db.commit()
            logger.info(f"[push] {titulo} — {enviados} notificação(ões) enviada(s)")
    finally:
        db.close()


# ── Inicialização do scheduler ────────────────────────────────────────────────

def iniciar_scheduler(
    vapid_private: str = "",
    vapid_public: str = "",
    vapid_subject: str = "",
) -> AsyncIOScheduler:
    global _vapid_private, _vapid_public, _vapid_subject
    _vapid_private = vapid_private
    _vapid_public  = vapid_public
    _vapid_subject = vapid_subject

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(job_principal,    "interval", minutes=SYNC_INTERVAL_MINS, id="sync")
    scheduler.add_job(job_notificacoes, "interval", minutes=5,                  id="push")
    return scheduler
