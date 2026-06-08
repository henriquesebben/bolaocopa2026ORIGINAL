from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Jogador(Base):
    __tablename__ = "jogadores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(30), unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    palpites = relationship("Palpite", back_populates="jogador", cascade="all, delete-orphan")
    bonus = relationship("BonusPalpite", back_populates="jogador", uselist=False, cascade="all, delete-orphan")


class Palpite(Base):
    __tablename__ = "palpites"

    id = Column(Integer, primary_key=True, index=True)
    jogador_id = Column(Integer, ForeignKey("jogadores.id", ondelete="CASCADE"), nullable=False)
    jogo_id = Column(String(20), nullable=False)
    gols_casa = Column(Integer)
    gols_fora = Column(Integer)
    avanca = Column(String(10), nullable=True)  # "casa" ou "fora" — palpite em empate de mata-mata
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    jogador = relationship("Jogador", back_populates="palpites")

    __table_args__ = (
        UniqueConstraint("jogador_id", "jogo_id", name="uq_palpite_jogador_jogo"),
    )


class Resultado(Base):
    __tablename__ = "resultados"

    id = Column(Integer, primary_key=True, index=True)
    jogo_id = Column(String(20), unique=True, nullable=False)
    gols_casa = Column(Integer, nullable=False)
    gols_fora = Column(Integer, nullable=False)
    avanca = Column(String(10), nullable=True)  # "casa" ou "fora" — quem avançou em empate de mata-mata
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class BonusPalpite(Base):
    __tablename__ = "bonus_palpites"

    id = Column(Integer, primary_key=True, index=True)
    jogador_id = Column(Integer, ForeignKey("jogadores.id", ondelete="CASCADE"), unique=True, nullable=False)
    campeao = Column(String(50))
    artilheiro = Column(String(100))
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    jogador = relationship("Jogador", back_populates="bonus")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    jogador_id = Column(Integer, ForeignKey("jogadores.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String, nullable=False, unique=True)
    subscription_json = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class Oficial(Base):
    __tablename__ = "oficiais"

    id = Column(Integer, primary_key=True, default=1)
    campeao = Column(String(50))
    artilheiro = Column(String(100))
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class NotificacaoEnviada(Base):
    """Registra quais jogos já tiveram push enviado; sobrevive a reinícios do servidor."""
    __tablename__ = "notificacoes_enviadas"

    jogo_id = Column(String(20), primary_key=True)
    enviada_em = Column(DateTime(timezone=True), default=now_utc)


class JogoNomeReal(Base):
    """Permite ao admin registrar os times reais de jogos do mata-mata para o sync automático."""
    __tablename__ = "jogo_nomes_reais"

    jogo_id = Column(String(20), primary_key=True)
    casa_real = Column(String(50), nullable=False)
    fora_real = Column(String(50), nullable=False)
    atualizado_em = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
