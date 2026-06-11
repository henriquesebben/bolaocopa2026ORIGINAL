import json
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    criar_token,
    exigir_dono_ou_admin,
    get_admin_atual,
    get_jogador_atual,
    hash_senha,
    verificar_senha,
)
from .database import Base, engine, get_db, SessionLocal
from . import models, schemas
from .jogos import JOGOS, JOGOS_POR_ID, TODOS_TIMES
from .sync import iniciar_scheduler, sync_manual, status_sync, _norm

# ── VAPID (Web Push) ──────────────────────────────────────────────────────────

_VAPID_KEY_FILE = Path(__file__).parent / "vapid_keys.json"


def _carregar_ou_gerar_vapid():
    """Carrega VAPID keys do env ou arquivo; gera se não existirem."""
    priv = os.getenv("VAPID_PRIVATE_KEY")
    pub  = os.getenv("VAPID_PUBLIC_KEY")
    if priv and pub:
        return priv, pub
    if _VAPID_KEY_FILE.exists():
        data = json.loads(_VAPID_KEY_FILE.read_text())
        return data["private"], data["public"]
    # Gera novas chaves
    import base64
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    v = Vapid()
    v.generate_keys()
    priv = v.private_pem().decode()
    public_key = v.public_key
    if public_key is None:
        raise RuntimeError("Falha ao gerar chave pública VAPID")
    pub_bytes = public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    _VAPID_KEY_FILE.write_text(json.dumps({"private": priv, "public": pub_b64}))
    return priv, pub_b64


try:
    VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY = _carregar_ou_gerar_vapid()
except Exception:
    VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY = "", ""

VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:henriquesebben@gmail.com")

# ── Inicialização ─────────────────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

allow_origins = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "").split(",") if o.strip()]
if not allow_origins:
    allow_origins = ["*"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Cria tabelas e executa migrações de colunas novas
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE palpites ADD COLUMN avanca VARCHAR(10)",
            "ALTER TABLE resultados ADD COLUMN avanca VARCHAR(10)",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # coluna já existe

    # Cria admin padrão se não existir
    db = SessionLocal()
    try:
        admin_nome = os.getenv("ADMIN_NOME", "Henrique Sebben")
        admin_senha = os.getenv("ADMIN_SENHA", "copa2026")
        if admin_senha == "copa2026":
            import warnings
            warnings.warn(
                "Usando senha padrão para admin. Defina ADMIN_SENHA no ambiente para produção.",
                UserWarning,
            )
        if not db.query(models.Jogador).filter(models.Jogador.nome == admin_nome).first():
            db.add(models.Jogador(
                nome=admin_nome,
                senha_hash=hash_senha(admin_senha),
                is_admin=True,
            ))
            db.commit()
    finally:
        db.close()

    scheduler = iniciar_scheduler(VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_SUBJECT)
    scheduler.start()

    yield

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(title="Bolão Copa 2026", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pontuação (portada do JS) ─────────────────────────────────────────────────

def calcular_pontos_jogo(
    palpite: models.Palpite,
    resultado: models.Resultado,
    multiplicador: int,
    eh_mata_mata: bool,
) -> Tuple[int, Optional[str]]:
    """Retorna (pontos, stat_key). stat_key: 'placar_exato' | 'vencedor_mais_gols' | 'so_vencedor' | 'gols_de_um_time' | None."""
    if palpite.gols_casa is None or palpite.gols_fora is None:
        return 0, None

    pc, pf = palpite.gols_casa, palpite.gols_fora
    rc, rf = resultado.gols_casa, resultado.gols_fora

    if eh_mata_mata:
        # Determina quem avança em cada lado (resultado real e palpite)
        resultado_avanca = resultado.avanca if rc == rf else ("casa" if rc > rf else "fora")
        palpite_avanca = palpite.avanca if pc == pf else ("casa" if pc > pf else "fora")
        acertou_avanca = bool(resultado_avanca and palpite_avanca == resultado_avanca)
        placar_exato = (pc == rc and pf == rf)
        # Palpitou empate E jogo terminou empatado nos 90min (mas placar diferente)
        acertou_empate = (pc == pf and rc == rf and not placar_exato)

        if placar_exato and acertou_avanca:
            return 10 * multiplicador, "placar_exato"
        if placar_exato:
            # Acertou o placar dos 90 min mas errou quem avança
            return 5 * multiplicador, None
        if acertou_empate and acertou_avanca:
            # Acertou que terminaria empatado + quem avança
            return 7 * multiplicador, "vencedor_mais_gols"
        if acertou_avanca:
            return 5 * multiplicador, "so_vencedor"
        if acertou_empate:
            # Acertou que terminaria empatado mas errou quem avança
            return 2 * multiplicador, "gols_de_um_time"
        if pc == rc or pf == rf:
            return 1 * multiplicador, "gols_de_um_time"
        return 0, None
    else:
        # Fase de grupos / 3° lugar
        if pc == rc and pf == rf:
            return 10, "placar_exato"
        if pc == pf and rc == rf:
            return 5, "so_vencedor"
        if (pc > pf and rc > rf) or (pc < pf and rc < rf):
            if pc == rc or pf == rf:
                return 7, "vencedor_mais_gols"
            return 5, "so_vencedor"
        if pc == rc or pf == rf:
            return 2, "gols_de_um_time"
        return 0, None


def calcular_pontos_total(
    jogador: models.Jogador,
    resultados_map: dict,
    oficiais: Optional[models.Oficial],
) -> Tuple[int, dict, bool, bool]:
    """Retorna (total, stats, acertou_campeao, acertou_artilheiro)."""
    total = 0
    stats = {
        "placar_exato": 0,
        "vencedor_mais_gols": 0,
        "so_vencedor": 0,
        "gols_de_um_time": 0,
        "resultado_correto": 0,
    }

    palpites_map = {p.jogo_id: p for p in jogador.palpites}

    for jogo in JOGOS:
        resultado = resultados_map.get(jogo["id"])
        palpite = palpites_map.get(jogo["id"])
        if not palpite or not resultado:
            continue

        pts, stat = calcular_pontos_jogo(palpite, resultado, jogo["multiplicador"], jogo["eh_mata_mata"])
        total += pts

        if stat:
            stats[stat] += 1
            if stat in ("placar_exato", "vencedor_mais_gols", "so_vencedor"):
                stats["resultado_correto"] += 1

    acertou_campeao = False
    acertou_artilheiro = False

    if oficiais and jogador.bonus:
        if oficiais.campeao and jogador.bonus.campeao == oficiais.campeao:
            total += 20
            acertou_campeao = True

        if (oficiais.artilheiro and jogador.bonus.artilheiro and
                _norm(jogador.bonus.artilheiro) == _norm(oficiais.artilheiro)):
            total += 20
            acertou_artilheiro = True

    return total, stats, acertou_campeao, acertou_artilheiro


# ── Auth ──────────────────────────────────────────────────────────────────────

_login_attempts: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW_SECONDS = 60


def _verificar_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - _LOGIN_WINDOW_SECONDS
    recent = [t for t in _login_attempts[ip] if t > window_start]
    _login_attempts[ip] = recent
    if len(recent) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas. Aguarde {_LOGIN_WINDOW_SECONDS} segundos.",
        )
    _login_attempts[ip].append(now)


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(request: Request, body: schemas.LoginRequest, db: Session = Depends(get_db)):
    _verificar_rate_limit(request.client.host if request.client else "unknown")
    jogador = db.query(models.Jogador).filter(models.Jogador.nome == body.nome).first()
    if not jogador or not verificar_senha(body.senha, jogador.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nome ou senha incorretos")
    token = criar_token(jogador.id, jogador.nome, jogador.is_admin)
    return schemas.TokenResponse(
        access_token=token,
        jogador_id=jogador.id,
        nome=jogador.nome,
        is_admin=jogador.is_admin,
    )


@app.post("/api/auth/registrar", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def registrar(body: schemas.JogadorCreate, db: Session = Depends(get_db)):
    if db.query(models.Jogador).filter(models.Jogador.nome == body.nome).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esse nome já está em uso")
    jogador = models.Jogador(nome=body.nome, senha_hash=hash_senha(body.senha))
    db.add(jogador)
    db.commit()
    db.refresh(jogador)
    token = criar_token(jogador.id, jogador.nome, jogador.is_admin)
    return schemas.TokenResponse(
        access_token=token,
        jogador_id=jogador.id,
        nome=jogador.nome,
        is_admin=jogador.is_admin,
    )


# ── Jogadores ─────────────────────────────────────────────────────────────────

@app.get("/api/jogadores", response_model=List[schemas.JogadorOut])
def listar_jogadores(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    jogadores = db.query(models.Jogador).all()
    result = []
    for j in jogadores:
        out = schemas.JogadorOut(
            id=j.id,
            nome=j.nome,
            is_admin=j.is_admin,
            total_palpites=len(j.palpites),
        )
        result.append(out)
    return result


@app.post("/api/jogadores", response_model=schemas.JogadorOut, status_code=status.HTTP_201_CREATED)
def criar_jogador(body: schemas.JogadorCreate, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    if db.query(models.Jogador).filter(models.Jogador.nome == body.nome).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um jogador com esse nome")
    jogador = models.Jogador(nome=body.nome, senha_hash=hash_senha(body.senha))
    db.add(jogador)
    db.commit()
    db.refresh(jogador)
    return schemas.JogadorOut(id=jogador.id, nome=jogador.nome, is_admin=jogador.is_admin, total_palpites=0)


@app.put("/api/jogadores/{jogador_id}/senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(jogador_id: int, body: schemas.RedefinirSenhaRequest, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    jogador = db.query(models.Jogador).filter(models.Jogador.id == jogador_id).first()
    if not jogador:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    if len(body.nova_senha) < 4:
        raise HTTPException(status_code=400, detail="Senha muito curta (mínimo 4 caracteres)")
    jogador.senha_hash = hash_senha(body.nova_senha)
    db.commit()


@app.delete("/api/jogadores/{jogador_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_jogador(jogador_id: int, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    jogador = db.query(models.Jogador).filter(models.Jogador.id == jogador_id).first()
    if not jogador:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    if jogador.is_admin:
        raise HTTPException(status_code=400, detail="Não é possível remover o admin")
    db.delete(jogador)
    db.commit()


# ── Jogos ─────────────────────────────────────────────────────────────────────

@app.get("/api/jogos")
def listar_jogos(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    nomes_reais = {r.jogo_id: r for r in db.query(models.JogoNomeReal).all()}
    jogos = []
    for j in JOGOS:
        jogo = dict(j)
        if j["id"] in nomes_reais:
            r = nomes_reais[j["id"]]
            if r.casa_real:
                jogo["casa"] = r.casa_real
            if r.fora_real:
                jogo["fora"] = r.fora_real
        jogos.append(jogo)
    return JSONResponse(content=jogos, headers={"Cache-Control": "no-store"})


@app.get("/api/times")
def listar_times(_=Depends(get_jogador_atual)):
    return TODOS_TIMES


# ── Palpites ──────────────────────────────────────────────────────────────────

def _jogo_travado(jogo: dict) -> bool:
    """Retorna True se o prazo de palpites já encerrou (10 min antes do início BRT)."""
    BRT = timezone(timedelta(hours=-3))
    ano, mes, dia = map(int, jogo["data"].split("-"))
    hora, minuto = map(int, jogo["horario"].split(":"))
    inicio_brt = datetime(ano, mes, dia, hora, minuto, tzinfo=BRT)
    limite = inicio_brt - timedelta(minutes=10)
    return datetime.now(timezone.utc) >= limite.astimezone(timezone.utc)


@app.get("/api/palpites/publicos")
def ver_palpites_publicos(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    """Palpites de todos os jogadores, apenas para jogos já travados.
    Considera travado: horário passou OU resultado já foi registrado."""
    com_resultado = {r.jogo_id for r in db.query(models.Resultado).all()}
    resultado: dict = {}
    for jogo in JOGOS:
        if not _jogo_travado(jogo) and jogo["id"] not in com_resultado:
            continue
        rows = (
            db.query(models.Palpite, models.Jogador)
            .join(models.Jogador, models.Jogador.id == models.Palpite.jogador_id)
            .filter(models.Palpite.jogo_id == jogo["id"])
            .all()
        )
        resultado[jogo["id"]] = [
            {
                "jogador_id": j.id,
                "nome": j.nome,
                "gols_casa": p.gols_casa,
                "gols_fora": p.gols_fora,
                "avanca": p.avanca,
            }
            for p, j in rows
        ]
    return resultado


@app.get("/api/palpites/{jogador_id}", response_model=List[schemas.PalpiteOut])
def ver_palpites(jogador_id: int, db: Session = Depends(get_db), atual=Depends(get_jogador_atual)):
    exigir_dono_ou_admin(jogador_id, atual)
    palpites = db.query(models.Palpite).filter(models.Palpite.jogador_id == jogador_id).all()
    return [schemas.PalpiteOut(jogo_id=p.jogo_id, gols_casa=p.gols_casa, gols_fora=p.gols_fora, avanca=p.avanca) for p in palpites]


@app.delete("/api/palpites/{jogador_id}")
def limpar_palpites(jogador_id: int, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    """Admin: apaga todos os palpites de um jogador sem remover o cadastro."""
    db.query(models.Palpite).filter(models.Palpite.jogador_id == jogador_id).delete()
    db.commit()
    return {"ok": True}


@app.put("/api/palpites/{jogador_id}/{jogo_id}", response_model=schemas.PalpiteOut)
def salvar_palpite(
    jogador_id: int,
    jogo_id: str,
    body: schemas.PalpiteUpsert,
    db: Session = Depends(get_db),
    atual=Depends(get_jogador_atual),
):
    exigir_dono_ou_admin(jogador_id, atual)

    if jogo_id not in JOGOS_POR_ID:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    # Palpite trava se o jogo já tem resultado oficial
    resultado = db.query(models.Resultado).filter(models.Resultado.jogo_id == jogo_id).first()
    if resultado and not atual.is_admin:
        raise HTTPException(status_code=400, detail="Esse jogo já tem resultado — palpite travado")

    # Palpite trava 10 minutos antes do jogo começar
    if not atual.is_admin:
        jogo_info = JOGOS_POR_ID[jogo_id]
        ano, mes, dia = map(int, jogo_info["data"].split("-"))
        hora, minuto = map(int, jogo_info["horario"].split(":"))
        BRT = timezone(timedelta(hours=-3))
        inicio_brt = datetime(ano, mes, dia, hora, minuto, tzinfo=BRT)
        limite = inicio_brt - timedelta(minutes=10)
        if datetime.now(timezone.utc) >= limite.astimezone(timezone.utc):
            raise HTTPException(status_code=400, detail="Prazo encerrado — palpites travam 10 min antes do jogo")

    if body.gols_casa is None or body.gols_fora is None:
        raise HTTPException(status_code=400, detail="Preencha gols de casa e gols de fora")

    # Em empate de mata-mata, avança é obrigatório
    jogo_meta = JOGOS_POR_ID[jogo_id]
    if (jogo_meta["eh_mata_mata"]
            and body.gols_casa == body.gols_fora
            and not body.avanca):
        raise HTTPException(status_code=400, detail="Empate em mata-mata exige informar quem avança")

    avanca = body.avanca if (body.gols_casa == body.gols_fora) else None

    palpite = (
        db.query(models.Palpite)
        .filter(models.Palpite.jogador_id == jogador_id, models.Palpite.jogo_id == jogo_id)
        .with_for_update()
        .first()
    )

    if palpite:
        palpite.gols_casa = body.gols_casa
        palpite.gols_fora = body.gols_fora
        palpite.avanca = avanca
    else:
        palpite = models.Palpite(
            jogador_id=jogador_id,
            jogo_id=jogo_id,
            gols_casa=body.gols_casa,
            gols_fora=body.gols_fora,
            avanca=avanca,
        )
        db.add(palpite)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            palpite = (
                db.query(models.Palpite)
                .filter(models.Palpite.jogador_id == jogador_id, models.Palpite.jogo_id == jogo_id)
                .first()
            )
            palpite.gols_casa = body.gols_casa
            palpite.gols_fora = body.gols_fora
            palpite.avanca = avanca

    db.commit()
    db.refresh(palpite)
    return schemas.PalpiteOut(
        jogo_id=palpite.jogo_id,
        gols_casa=palpite.gols_casa,
        gols_fora=palpite.gols_fora,
        avanca=palpite.avanca,
    )


# ── Resultados ────────────────────────────────────────────────────────────────

@app.get("/api/resultados", response_model=List[schemas.ResultadoOut])
def listar_resultados(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    return db.query(models.Resultado).all()


def _propagar_progressao(jogo_id: str, gols_casa: int, gols_fora: int, avanca: Optional[str], db: Session) -> None:
    """Após salvar resultado de mata-mata, atualiza automaticamente os times dos próximos confrontos."""
    jogo_meta = JOGOS_POR_ID.get(jogo_id)
    if not jogo_meta or not jogo_meta["eh_mata_mata"]:
        return

    if gols_casa > gols_fora:
        slot_vencedor, slot_perdedor = "casa", "fora"
    elif gols_fora > gols_casa:
        slot_vencedor, slot_perdedor = "fora", "casa"
    else:
        slot_vencedor = avanca
        slot_perdedor = "fora" if avanca == "casa" else "casa"

    if not slot_vencedor:
        return

    nome_real = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == jogo_id).first()
    if slot_vencedor == "casa":
        nome_vencedor = (nome_real.casa_real if nome_real and nome_real.casa_real else None) or jogo_meta["casa"]
        nome_perdedor = (nome_real.fora_real if nome_real and nome_real.fora_real else None) or jogo_meta["fora"]
    else:
        nome_vencedor = (nome_real.fora_real if nome_real and nome_real.fora_real else None) or jogo_meta["fora"]
        nome_perdedor = (nome_real.casa_real if nome_real and nome_real.casa_real else None) or jogo_meta["casa"]

    tag_vencedor = f"Vencedor {jogo_id}"
    tag_perdedor = f"Perdedor {jogo_id}"

    for proximo in JOGOS:
        novo_casa = novo_fora = None
        if proximo["casa"] == tag_vencedor:
            novo_casa = nome_vencedor
        elif proximo["casa"] == tag_perdedor:
            novo_casa = nome_perdedor
        if proximo["fora"] == tag_vencedor:
            novo_fora = nome_vencedor
        elif proximo["fora"] == tag_perdedor:
            novo_fora = nome_perdedor

        if novo_casa is None and novo_fora is None:
            continue

        rec = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == proximo["id"]).first()
        if rec:
            if novo_casa is not None:
                rec.casa_real = novo_casa
            if novo_fora is not None:
                rec.fora_real = novo_fora
        else:
            db.add(models.JogoNomeReal(
                jogo_id=proximo["id"],
                casa_real=novo_casa or proximo["casa"],
                fora_real=novo_fora or proximo["fora"],
            ))


@app.put("/api/resultados/{jogo_id}", response_model=schemas.ResultadoOut)
def salvar_resultado(
    jogo_id: str,
    body: schemas.ResultadoUpsert,
    db: Session = Depends(get_db),
    _=Depends(get_admin_atual),
):
    if jogo_id not in JOGOS_POR_ID:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    jogo_meta = JOGOS_POR_ID[jogo_id]
    if (jogo_meta["eh_mata_mata"] and body.gols_casa == body.gols_fora and not body.avanca):
        raise HTTPException(status_code=400, detail="Empate em mata-mata exige informar quem avançou")

    avanca = body.avanca if body.gols_casa == body.gols_fora else None

    resultado = (
        db.query(models.Resultado)
        .filter(models.Resultado.jogo_id == jogo_id)
        .with_for_update()
        .first()
    )
    if resultado:
        resultado.gols_casa = body.gols_casa
        resultado.gols_fora = body.gols_fora
        resultado.avanca = avanca
    else:
        resultado = models.Resultado(jogo_id=jogo_id, gols_casa=body.gols_casa, gols_fora=body.gols_fora, avanca=avanca)
        db.add(resultado)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            resultado = db.query(models.Resultado).filter(models.Resultado.jogo_id == jogo_id).first()
            resultado.gols_casa = body.gols_casa
            resultado.gols_fora = body.gols_fora
            resultado.avanca = avanca

    _propagar_progressao(jogo_id, body.gols_casa, body.gols_fora, avanca, db)
    db.commit()
    db.refresh(resultado)
    return resultado


@app.delete("/api/resultados/{jogo_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_resultado(jogo_id: str, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    resultado = db.query(models.Resultado).filter(models.Resultado.jogo_id == jogo_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado não encontrado")
    db.delete(resultado)
    db.commit()


# ── Bônus ─────────────────────────────────────────────────────────────────────

@app.get("/api/bonus/{jogador_id}", response_model=schemas.BonusOut)
def ver_bonus(jogador_id: int, db: Session = Depends(get_db), atual=Depends(get_jogador_atual)):
    exigir_dono_ou_admin(jogador_id, atual)
    bonus = db.query(models.BonusPalpite).filter(models.BonusPalpite.jogador_id == jogador_id).first()
    if not bonus:
        return schemas.BonusOut(campeao=None, artilheiro=None)
    return schemas.BonusOut(campeao=bonus.campeao, artilheiro=bonus.artilheiro)


@app.put("/api/bonus/{jogador_id}", response_model=schemas.BonusOut)
def salvar_bonus(
    jogador_id: int,
    body: schemas.BonusUpsert,
    db: Session = Depends(get_db),
    atual=Depends(get_jogador_atual),
):
    exigir_dono_ou_admin(jogador_id, atual)

    if not atual.is_admin:
        BRT = timezone(timedelta(hours=-3))
        prazo = datetime(2026, 6, 11, 15, 50, tzinfo=BRT)
        if datetime.now(timezone.utc) >= prazo.astimezone(timezone.utc):
            raise HTTPException(status_code=400, detail="Prazo encerrado — palpites bônus travaram em 11/06 às 15h50 (Brasília)")

    bonus = db.query(models.BonusPalpite).filter(models.BonusPalpite.jogador_id == jogador_id).first()
    if bonus:
        bonus.campeao = body.campeao
        bonus.artilheiro = body.artilheiro
    else:
        bonus = models.BonusPalpite(jogador_id=jogador_id, campeao=body.campeao, artilheiro=body.artilheiro)
        db.add(bonus)
    db.commit()
    db.refresh(bonus)
    return schemas.BonusOut(campeao=bonus.campeao, artilheiro=bonus.artilheiro)


# ── Oficiais ──────────────────────────────────────────────────────────────────

@app.get("/api/oficiais", response_model=schemas.OficiaisOut)
def ver_oficiais(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    oficial = db.query(models.Oficial).filter(models.Oficial.id == 1).first()
    if not oficial:
        return schemas.OficiaisOut(campeao=None, artilheiro=None)
    return schemas.OficiaisOut(campeao=oficial.campeao, artilheiro=oficial.artilheiro)


@app.put("/api/oficiais", response_model=schemas.OficiaisOut)
def salvar_oficiais(body: schemas.OficiaisUpsert, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    oficial = db.query(models.Oficial).filter(models.Oficial.id == 1).first()
    if oficial:
        oficial.campeao = body.campeao
        oficial.artilheiro = body.artilheiro
    else:
        oficial = models.Oficial(id=1, campeao=body.campeao, artilheiro=body.artilheiro)
        db.add(oficial)
    db.commit()
    db.refresh(oficial)
    return schemas.OficiaisOut(campeao=oficial.campeao, artilheiro=oficial.artilheiro)


# ── Ranking ───────────────────────────────────────────────────────────────────

@app.get("/api/ranking", response_model=List[schemas.RankingEntry])
def ranking(db: Session = Depends(get_db), _=Depends(get_jogador_atual)):
    jogadores = db.query(models.Jogador).all()
    resultados = db.query(models.Resultado).all()
    resultados_map = {r.jogo_id: r for r in resultados}
    oficial = db.query(models.Oficial).filter(models.Oficial.id == 1).first()

    entradas = []
    for j in jogadores:
        total, stats, acertou_campeao, acertou_artilheiro = calcular_pontos_total(j, resultados_map, oficial)
        entradas.append({
            "jogador": j,
            "total": total,
            "acertou_campeao": acertou_campeao,
            "acertou_artilheiro": acertou_artilheiro,
            "campeao_palpite": j.bonus.campeao if j.bonus else None,
            "artilheiro_palpite": j.bonus.artilheiro if j.bonus else None,
            **stats,
        })

    # Desempate: 1° placar exato · 2° resultado correto · 3° artilheiro · 4° campeão
    entradas.sort(key=lambda e: (
        -e["total"],
        -e["placar_exato"],
        -e["resultado_correto"],
        -e["acertou_artilheiro"],
        -e["acertou_campeao"],
    ))

    return [
        schemas.RankingEntry(
            posicao=i + 1,
            jogador_id=e["jogador"].id,
            nome=e["jogador"].nome,
            total=e["total"],
            placar_exato=e["placar_exato"],
            resultado_correto=e["resultado_correto"],
            acertou_artilheiro=e["acertou_artilheiro"],
            acertou_campeao=e["acertou_campeao"],
            artilheiro_palpite=e["artilheiro_palpite"],
            campeao_palpite=e["campeao_palpite"],
            vencedor_mais_gols=e["vencedor_mais_gols"],
            so_vencedor=e["so_vencedor"],
            gols_de_um_time=e["gols_de_um_time"],
        )
        for i, e in enumerate(entradas)
    ]


# ── Sync automático ──────────────────────────────────────────────────────────

@app.post("/api/admin/sync")
async def sync_agora(_=Depends(get_admin_atual)):
    resultado = await sync_manual()
    return resultado


@app.get("/api/admin/sync/status")
def sync_status(_=Depends(get_admin_atual)):
    return status_sync()


# ── Mata-mata: registrar times reais para sync automático ────────────────────

@app.get("/api/admin/jogo-nomes-reais")
def listar_jogo_nomes_reais(db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    return [
        {"jogo_id": r.jogo_id, "casa_real": r.casa_real, "fora_real": r.fora_real}
        for r in db.query(models.JogoNomeReal).all()
    ]


@app.delete("/api/admin/jogo/{jogo_id}/times", status_code=status.HTTP_204_NO_CONTENT)
def limpar_times_jogo(jogo_id: str, db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == jogo_id).delete()
    db.commit()


@app.delete("/api/admin/jogo-nomes-reais", status_code=status.HTTP_204_NO_CONTENT)
def limpar_todos_times(db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    db.query(models.JogoNomeReal).delete()
    db.commit()


@app.post("/api/admin/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_bolao(db: Session = Depends(get_db), _=Depends(get_admin_atual)):
    """Apaga palpites, bônus, resultados e times do mata-mata. Preserva os cadastros."""
    db.query(models.Palpite).delete()
    db.query(models.BonusPalpite).delete()
    db.query(models.Resultado).delete()
    db.query(models.JogoNomeReal).delete()
    oficial = db.query(models.Oficial).filter(models.Oficial.id == 1).first()
    if oficial:
        oficial.campeao = None
        oficial.artilheiro = None
    db.commit()


@app.put("/api/admin/jogo/{jogo_id}/times")
def atualizar_times_mata_mata(
    jogo_id: str,
    body: schemas.JogoTimesUpsert,
    db: Session = Depends(get_db),
    _=Depends(get_admin_atual),
):
    if jogo_id not in JOGOS_POR_ID:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    rec = db.query(models.JogoNomeReal).filter(models.JogoNomeReal.jogo_id == jogo_id).first()
    if rec:
        rec.casa_real = body.casa
        rec.fora_real = body.fora
    else:
        db.add(models.JogoNomeReal(jogo_id=jogo_id, casa_real=body.casa, fora_real=body.fora))
    db.commit()
    return {"ok": True}


# ── Web Push ───────────────────────────────────────────────────────────────────

@app.get("/api/push/vapid-key")
def vapid_key(_=Depends(get_jogador_atual)):
    return {"public_key": VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe_push(body: schemas.PushSubscribeRequest, db: Session = Depends(get_db), atual=Depends(get_jogador_atual)):
    sub_json = json.dumps(body.model_dump())
    existing = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == body.endpoint
    ).first()
    if existing:
        existing.jogador_id = atual.id
        existing.subscription_json = sub_json
    else:
        db.add(models.PushSubscription(
            jogador_id=atual.id,
            endpoint=body.endpoint,
            subscription_json=sub_json,
        ))
    db.commit()


@app.delete("/api/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_push(body: schemas.PushUnsubscribeRequest, db: Session = Depends(get_db), atual=Depends(get_jogador_atual)):
    db.query(models.PushSubscription).filter(
        models.PushSubscription.jogador_id == atual.id,
        models.PushSubscription.endpoint == body.endpoint,
    ).delete()
    db.commit()


# ── Frontend (serve arquivos estáticos + SPA fallback) ────────────────────────
# Deve vir após todas as rotas /api para não interceptá-las (Starlette: primeiro match vence)

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    reload_on_change = os.getenv("ENV", "development").lower() != "production"
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=reload_on_change)
