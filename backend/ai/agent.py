"""Dispatcher do agente IA — escolhe o provider baseado nas variaveis de ambiente.

Prioridade (em ordem):
  1. LLM_PROVIDER=anthropic|gemini (escolha explicita)
  2. Auto: GEMINI_API_KEY presente -> Gemini; senao ANTHROPIC_API_KEY -> Claude
"""
import logging

from sqlalchemy.orm import Session

from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _escolher_provider() -> str:
    s = get_settings()
    if s.llm_provider:
        return s.llm_provider.lower()
    if s.gemini_api_key:
        return "gemini"
    if s.anthropic_api_key:
        return "anthropic"
    raise RuntimeError(
        "Nenhuma chave de LLM configurada. Defina GEMINI_API_KEY (free) ou ANTHROPIC_API_KEY no .env."
    )


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    """Roteia pra o provider correto. Mesma assinatura, mesmo retorno."""
    provider = _escolher_provider()
    logger.info("agent.provider=%s", provider)
    if provider == "gemini":
        from .providers import gemini
        return gemini.responder(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)
    if provider == "anthropic":
        from .providers import claude
        return claude.responder(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)
    raise RuntimeError(f"provider desconhecido: {provider}")
