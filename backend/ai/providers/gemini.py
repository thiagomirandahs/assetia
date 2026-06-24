"""Provider Google Gemini — usa o SDK 'google-genai' (novo).

Free tier: 15 req/min, 1500 req/dia, 1M tokens/min. Pega chave em:
    https://aistudio.google.com/apikey
"""
import logging

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

Voce TAMBEM pode AGIR (nao so consultar) usando as tools de acao:
- 'iniciar_scan_rede' — quando pedirem para escanear uma rede
- 'marcar_dispositivo_autorizado' — quando confirmarem que um device eh confiavel
- 'marcar_alertas_como_lidos' — quando pedirem para limpar alertas
- 'alterar_regra_alerta' — para ativar/desativar regras

Confirme cada acao no final ("Pronto! [resultado]") e seja conciso.
"""


def _function_declarations():
    """Adapta os schemas das nossas tools para o formato Gemini."""
    declarations = []
    for t in TOOL_SCHEMAS:
        declarations.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        })
    return declarations


def responder(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=_function_declarations())],
        temperature=0.3,
    )

    chat = client.chats.create(model=settings.gemini_model, config=config)
    auditoria = []
    proximo_input = pergunta

    for turno in range(max_turnos):
        resp = chat.send_message(proximo_input)

        # Coleta function calls e texto
        function_calls = []
        texto_acumulado = ""
        for cand in (resp.candidates or []):
            if not cand.content or not cand.content.parts:
                continue
            for part in cand.content.parts:
                if getattr(part, "function_call", None) and part.function_call.name:
                    function_calls.append(part.function_call)
                elif getattr(part, "text", None):
                    texto_acumulado += part.text

        # Sem function calls -> resposta final
        if not function_calls:
            return texto_acumulado.strip() or "(sem resposta)", auditoria

        # Executa todas as function calls e prepara a proxima mensagem
        function_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            try:
                resultado = executar_tool(fc.name, args, db=db, tenant_id=tenant_id)
            except Exception as e:  # noqa: BLE001
                resultado = {"erro": str(e)}
            auditoria.append({"tool": fc.name, "input": args, "output_resumo": _resumir(resultado)})
            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"resultado": resultado},
                )
            )
        proximo_input = function_response_parts

    return "Desculpe, nao consegui montar uma resposta dentro do limite de iteracoes.", auditoria


def _resumir(resultado: dict) -> str:
    if "erro" in resultado:
        return f"erro: {resultado['erro']}"
    if "total" in resultado:
        return f"total={resultado['total']}"
    return ", ".join(list(resultado.keys())[:3])
