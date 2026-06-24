"""Modelos SQLAlchemy 2.0 (declarative)."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # 'admin' | 'user'
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Device(Base):
    """Dispositivo descoberto na rede."""
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fabricante: Mapped[str | None] = mapped_column(String(120), nullable=True)  # via OUI
    so: Mapped[str | None] = mapped_column(String(80), nullable=True)             # Windows/Linux/...
    tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)           # servidor/estacao/impressora/IoT
    vlan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)         # CSV simples

    online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primeira_visao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    ultima_visao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="devices")

    __table_args__ = (
        Index("ix_devices_tenant_ip", "tenant_id", "ip"),
        Index("ix_devices_tenant_mac", "tenant_id", "mac"),
        Index("ix_devices_tenant_online", "tenant_id", "online"),
    )


class Scan(Base):
    """Uma execucao do scanner."""
    __tablename__ = "scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    rede: Mapped[str] = mapped_column(String(50), nullable=False)  # ex: 192.168.1.0/24
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    achados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    novos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="rodando", nullable=False)  # rodando/concluido/erro
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChatMessage(Base):
    """Mensagens trocadas entre usuario e agente IA."""
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)   # 'user' | 'assistant'
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
