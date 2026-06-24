"""Agente IA: Claude responde perguntas sobre o inventario via tool use.

Fluxo:
  1. Recebe pergunta em PT-BR
  2. Chama Claude com lista de ferramentas (tools.TOOL_SCHEMAS)
  3. Se Claude pedir uma ferramenta, executa contra o banco e devolve resultado
  4. Loop ate Claude parar de pedir tools e retornar texto final
"""
import json
import logging

from anthropic import Anthropic
from sqlalchemy.orm import Session

from ..core.config import get_settings
from .tools import TOOL_SCHEMAS, executar_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Voce e o AssetIA, um assistente de TI que ajuda administradores a entender o inventario de dispositivos da rede da empresa.

Voce tem acesso a um banco de dados de dispositivos via ferramentas (tools). USE as ferramentas para responder com dados reais — NUNCA invente informacoes.

Regras:
- Responda SEMPRE em portugues brasileiro, de forma direta e amigavel.
- Use linguagem tecnica quando apropriado mas sem exagero.
- Se a pergunta nao for sobre o inventario (ex: "como esta o tempo?"), educadamente diga que voce so ajuda com perguntas sobre o inventario de TI.
- Quando listar dispositivos, mostre maximo 10 e diga "(+ N outros)" se houver mais.
- Para perguntas tipo "tudo bem na rede?", chame `resumo_inventario` e comente os dados.
- Quando encontrar algo suspeito (device novo desconhecido, muitos offline ha tempo), sinalize com ⚠️.
"""


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8) -> tuple[str, list[dict]]:
    """Roda o loop agente -> tool -> agente ate ter resposta final.

    Returns:
        (resposta_final, lista_de_chamadas_de_ferramenta_para_auditoria)
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY nao configurada no .env")

    client = Anthropic(api_key=settings.anthropic_api_key)
    mensagens = [{"role": "user", "content": pergunta}]
    auditoria: list[dict] = []

    for turno in range(max_turnos):
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=mensagens,
        )

        if resp.stop_reason == "end_turn":
            texto = "".join(b.text for b in resp.content if b.type == "text")
            return texto, auditoria

        if resp.stop_reason != "tool_use":
            # situacao inesperada, sai com o que tem
            texto = "".join(b.text for b in resp.content if b.type == "text")
            return texto or "(sem resposta)", auditoria

        # Adiciona a resposta do assistente (com tool calls) ao historico
        mensagens.append({"role": "assistant", "content": resp.content})

        # Executa cada tool pedida
        tool_results = []
        for bloco in resp.content:
            if bloco.type != "tool_use":
                continue
            logger.info("agent.tool", extra={"name": bloco.name, "input": bloco.input})
            try:
                resultado = executar_tool(bloco.name, bloco.input or {}, db=db, tenant_id=tenant_id)
            except Exception as e:  # noqa: BLE001
                resultado = {"erro": str(e)}
            auditoria.append({"tool": bloco.name, "input": bloco.input, "output_resumo": _resumir(resultado)})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": bloco.id,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

        mensagens.append({"role": "user", "content": tool_results})

    return "Desculpe, nao consegui montar uma resposta dentro do limite de iteracoes.", auditoria


def _resumir(resultado: dict) -> str:
    """Versao curta para log/auditoria."""
    if "erro" in resultado:
        return f"erro: {resultado['erro']}"
    if "total" in resultado:
        return f"total={resultado['total']}"
    return ", ".join(list(resultado.keys())[:3])
