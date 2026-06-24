"""Dispatcher do agente IA — escolhe o provider baseado nas variaveis de ambiente.

Prioridade (em ordem):
  1. LLM_PROVIDER=anthropic|gemini|groq (escolha explicita)
  2. Auto: detecta qual chave esta configurada
"""
import logging

from sqlalchemy.orm import Session

from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _escolher_provider() -> str:
    s = get_settings()
    if s.llm_provider:
        return s.llm_provider.lower()
    if s.groq_api_key:
        return "groq"
    if s.gemini_api_key:
        return "gemini"
    if s.anthropic_api_key:
        return "anthropic"
    raise RuntimeError(
        "Nenhuma chave de LLM configurada. Defina GROQ_API_KEY (mais free), "
        "GEMINI_API_KEY ou ANTHROPIC_API_KEY no .env."
    )


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    """Roteia para o provider correto. Mesma assinatura, mesmo retorno."""
    provider = _escolher_provider()
    logger.info("agent.provider=%s", provider)
    if provider == "groq":
        from .providers import groq as p
    elif provider == "gemini":
        from .providers import gemini as p
    elif provider == "anthropic":
        from .providers import claude as p
    else:
        raise RuntimeError(f"provider desconhecido: {provider}")
    return p.responder(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)
