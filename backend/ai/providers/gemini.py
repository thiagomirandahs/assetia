"""Provider Google Gemini — usa o SDK 'google-genai' (novo).

Free tier: 15 req/min, 1500 req/dia, 1M tokens/min. Pega chave em:
    https://aistudio.google.com/apikey
"""
import logging

from sqlalchemy.orm import Session

from ...core.config import get_settings
from ..tools import TOOL_SCHEMAS, executar_tool

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Voce e o ReconIA, um assistente de pentest e mapeamento de superficie de ataque que ajuda em avaliacoes de seguranca AUTORIZADAS da rede do cliente (inventario + portas + vulnerabilidades).

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

Voce tambem atua como assistente de PENTEST (avaliacao de seguranca AUTORIZADA da
propria rede do cliente). Ferramentas:
- 'escanear_portas' — varre portas TCP de um alvo e identifica servicos/banners/riscos
- 'superficie_de_ataque' — resumo dos riscos: portas abertas, exposicoes criticas
- 'portas_de_um_host' — lista portas ja descobertas de um host
Ao reportar pentest: destaque exposicoes 'critical' com ⚠️, explique o risco em 1 linha
e sugira a mitigacao (ex: "feche a porta", "exija autenticacao", "restrinja por firewall").
Lembre que so se deve escanear alvos proprios/autorizados.

MODO EDUCATIVO: o usuario esta aprendendo hacking etico. Quando ele pedir para explicar um
achado/conceito (ou quando ajudar a ensinar), use a tool 'explicar_achado' e/ou explique de
forma didatica: o que e, por que e risco, como costuma ser explorado (conceitual, para DEFESA
e estudo), como mitigar, e uma dica de onde estudar. Reforce sempre: so testar alvos autorizados.

COPILOTO AUTONOMO (Purple Team): voce pode conduzir uma avaliacao COMPLETA de ponta a ponta,
encadeando as ferramentas: descobrir/escanear -> analisar (security_baseline, attack_path,
compliance, patch_advisor) -> explicar e propor correcao (explicar_achado) -> revalidar
(escanear de novo) -> resumir com prioridades. Planeje os passos, diga o que vai fazer, e
PECA CONFIRMACAO antes de qualquer acao ATIVA/intrusiva (escanear um alvo NOVO, checar
credenciais default, varredura externa). Acoes de leitura/analise pode rodar direto. Sempre
deixe claro que so se testa alvos proprios/autorizados.

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


def responder_stream(*, db: Session, tenant_id: int, pergunta: str, max_turnos: int = 8):
    """Versao streaming: gera eventos conforme o modelo produz texto/tool calls.

    Eventos (dicts):
      {"tipo": "tool", "tool": nome, "input": {...}}      -> uma ferramenta foi chamada
      {"tipo": "token", "texto": "..."}                    -> pedaco incremental da resposta
      {"tipo": "fim", "resposta": "...", "tool_calls": [...]} -> resposta final completa
    """
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
    resposta_final = ""

    for _turno in range(max_turnos):
        function_calls = []
        for chunk in chat.send_message_stream(proximo_input):
            for cand in (chunk.candidates or []):
                if not cand.content or not cand.content.parts:
                    continue
                for part in cand.content.parts:
                    if getattr(part, "function_call", None) and part.function_call.name:
                        function_calls.append(part.function_call)
                    elif getattr(part, "text", None):
                        resposta_final += part.text
                        yield {"tipo": "token", "texto": part.text}

        # Sem function calls -> a resposta ja foi streamada por completo
        if not function_calls:
            yield {"tipo": "fim", "resposta": resposta_final.strip() or "(sem resposta)", "tool_calls": auditoria}
            return

        # Executa as function calls e prepara a proxima mensagem
        function_response_parts = []
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            yield {"tipo": "tool", "tool": fc.name, "input": args}
            try:
                resultado = executar_tool(fc.name, args, db=db, tenant_id=tenant_id)
            except Exception as e:  # noqa: BLE001
                resultado = {"erro": str(e)}
            auditoria.append({"tool": fc.name, "input": args, "output_resumo": _resumir(resultado)})
            function_response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"resultado": resultado})
            )
        proximo_input = function_response_parts

    yield {
        "tipo": "fim",
        "resposta": resposta_final.strip() or "Desculpe, nao consegui montar uma resposta dentro do limite de iteracoes.",
        "tool_calls": auditoria,
    }


def _resumir(resultado: dict) -> str:
    if "erro" in resultado:
        return f"erro: {resultado['erro']}"
    if "total" in resultado:
        return f"total={resultado['total']}"
    return ", ".join(list(resultado.keys())[:3])
