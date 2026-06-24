"""Pydantic schemas para entrada e saida da API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ===== Auth =====
class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nome: str
    role: str
    tenant_id: int


# ===== Device =====
class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ip: str
    mac: str | None
    hostname: str | None
    fabricante: str | None
    so: str | None
    tipo: str | None
    vlan: str | None
    tags: str | None
    online: bool
    primeira_visao: datetime
    ultima_visao: datetime


class DeviceListOut(BaseModel):
    total: int
    online: int
    offline: int
    devices: list[DeviceOut]


# ===== Scan =====
class ScanStartIn(BaseModel):
    rede: str = Field(..., description="Rede em formato CIDR, ex: 192.168.1.0/24")


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rede: str
    iniciado_em: datetime
    finalizado_em: datetime | None
    achados: int
    novos: int
    status: str
    erro: str | None


# ===== Chat =====
class ChatIn(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=2000)


class ChatOut(BaseModel):
    resposta: str
    tool_calls: list[dict] = []  # auditoria — quais ferramentas o agente chamou


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    conteudo: str
    criado_em: datetime
