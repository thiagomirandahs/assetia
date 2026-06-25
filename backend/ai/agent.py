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


def _carregar_provider(provider: str):
    """Importa e devolve o modulo do provider escolhido."""
    if provider == "groq":
        from .providers import groq as p
    elif provider == "gemini":
        from .providers import gemini as p
    elif provider == "anthropic":
        from .providers import claude as p
    else:
        raise RuntimeError(f"provider desconhecido: {provider}")
    return p


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    """Roteia para o provider correto. Mesma assinatura, mesmo retorno."""
    provider = _escolher_provider()
    logger.info("agent.provider=%s", provider)
    p = _carregar_provider(provider)
    return p.responder(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)


def responder_stream(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    """Gera eventos de streaming (token/tool/fim) do agente.

    Se o provider implementar `responder_stream`, usa streaming real. Caso contrario,
    chama o `responder` normal e emite o resultado como um unico bloco — assim o
    endpoint SSE funciona com qualquer provider.
    """
    provider = _escolher_provider()
    logger.info("agent.stream.provider=%s", provider)
    p = _carregar_provider(provider)

    if hasattr(p, "responder_stream"):
        yield from p.responder_stream(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)
        return

    # Fallback: provider sem streaming nativo.
    resposta, tool_calls = p.responder(db=db, tenant_id=tenant_id, pergunta=pergunta, max_turnos=max_turnos)
    for tc in (tool_calls or []):
        yield {"tipo": "tool", "tool": tc.get("tool"), "input": tc.get("input", {})}
    if resposta:
        yield {"tipo": "token", "texto": resposta}
    yield {"tipo": "fim", "resposta": resposta, "tool_calls": tool_calls or []}
