"""Provider Groq — API compativel com OpenAI, Llama 3.3 70B com tool use.

Free tier muito generoso. Pega chave em:
    https://console.groq.com/keys
"""
import json
import logging

from groq import Groq
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ..tools import TOOL_SCHEMAS, executar_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Voce e o AssetIA, um assistente de TI que ajuda administradores a entender o inventario de dispositivos da rede da empresa.

Voce tem acesso a um banco de dados de dispositivos via ferramentas (function calling). USE as ferramentas para responder com dados reais — NUNCA invente informacoes.

Regras:
- Responda SEMPRE em portugues brasileiro, de forma direta e amigavel.
- Use linguagem tecnica quando apropriado mas sem exagero.
- Se a pergunta nao for sobre o inventario (ex: "como esta o tempo?"), educadamente diga que voce so ajuda com perguntas sobre o inventario de TI.
- Quando listar dispositivos, mostre maximo 10 e diga "(+ N outros)" se houver mais.
- Para perguntas tipo "tudo bem na rede?", chame `resumo_inventario` e comente os dados.
- Quando encontrar algo suspeito (device novo desconhecido, muitos offline ha tempo), sinalize com ⚠️.
"""


def _tools_openai_format():
    """Groq usa formato OpenAI: { type: 'function', function: { name, description, parameters } }."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_SCHEMAS
    ]


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada")

    client = Groq(api_key=settings.groq_api_key)
    mensagens = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": pergunta},
    ]
    tools = _tools_openai_format()
    auditoria = []

    for _ in range(max_turnos):
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=mensagens,
            tools=tools,
            tool_choice="auto",
            max_tokens=1024,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip() or "(sem resposta)", auditoria

        # Adiciona a resposta do assistente (com tool_calls) ao historico
        mensagens.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            try:
                resultado = executar_tool(tc.function.name, args, db=db, tenant_id=tenant_id)
            except Exception as e:  # noqa: BLE001
                resultado = {"erro": str(e)}
            auditoria.append({"tool": tc.function.name, "input": args, "output_resumo": _resumir(resultado)})
            mensagens.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            })

    return "Desculpe, nao consegui montar uma resposta dentro do limite de iteracoes.", auditoria


def _resumir(resultado: dict) -> str:
    if "erro" in resultado:
        return f"erro: {resultado['erro']}"
    if "total" in resultado:
        return f"total={resultado['total']}"
    return ", ".join(list(resultado.keys())[:3])
