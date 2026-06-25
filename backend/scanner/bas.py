"""BAS — Breach & Attack Simulation com testes ATÔMICOS SEGUROS (estilo Atomic Red Team).

⚠️ NÃO executa ataques reais. Cada teste é BENIGNO e REVERSÍVEL, e serve só para verificar se
as defesas (AV/EDR/SIEM) DETECTAM a técnica — abordagem Purple Team. Mapeado ao MITRE ATT&CK.
USO em máquina própria/autorizada (lab). Roda apenas com confirmação explícita.
"""
import logging
import os
import platform
import subprocess
import tempfile
import time

logger = logging.getLogger(__name__)
_WIN = platform.system().lower() == "windows"
_FLAGS = 0x08000000 if _WIN else 0

# String EICAR montada em PARTES de propósito — assim ela NÃO existe literalmente neste arquivo
# (senão o próprio antivírus marcaria o .py). EICAR é o teste-padrão de AV, totalmente benigno.
_EICAR_PARTES = ["X5O!P%@AP[4\\PZX54(P^)7CC)7}", "$" + "EICAR-STANDARD-", "ANTIVIRUS-" + "TEST-FILE!" + "$H+H*"]


def _run(cmd, timeout=12):
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=_FLAGS)
        return (cp.stdout or "") + (cp.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"__erro__ {e}"


def _teste_av_eicar() -> dict:
    """T1105 — escreve o arquivo de teste EICAR e vê se o AV o remove (= detectou)."""
    base = {"tecnica": "Detecção de malware (arquivo de teste EICAR)", "mitre": "T1105", "modifica": "arquivo temp (auto-removido)"}
    caminho = os.path.join(tempfile.gettempdir(), "reconia_bas_eicar.com")
    try:
        with open(caminho, "w") as f:
            f.write("".join(_EICAR_PARTES))
    except Exception as e:  # noqa: BLE001
        return {**base, "executou": False, "bloqueado": None, "detalhe": f"não consegui escrever (AV bloqueou a escrita?): {e}"}
    time.sleep(2.0)
    removido = not os.path.exists(caminho)
    if not removido:
        try:
            os.remove(caminho)
        except Exception:  # noqa: BLE001
            pass
    return {**base, "executou": True, "bloqueado": removido,
            "detalhe": "AV removeu/quarentenou o arquivo (detecção OK)" if removido else "AV NÃO removeu o EICAR — revise sua proteção contra malware"}


def _teste_recon() -> dict:
    """T1082/T1033 — comandos de descoberta benignos. Testa se o EDR registra recon."""
    saida = _run(["whoami"] if not _WIN else ["cmd", "/c", "whoami & hostname"])
    ok = "__erro__" not in saida
    return {"tecnica": "Discovery — comandos de reconhecimento", "mitre": "T1082/T1033", "modifica": "nada (leitura)",
            "executou": ok, "bloqueado": None,
            "detalhe": "Comandos de recon executaram. Verifique se seu EDR/SIEM gerou log/alerta."}


def _teste_lolbin() -> dict:
    """T1140 — usa um LOLBin (certutil/base64) para decodificar string benigna."""
    if _WIN:
        saida = _run(["certutil", "-decodehex", "-f", "nul", "nul"])  # invoca certutil de forma inócua
        usou = "__erro__" not in saida or "certutil" in saida.lower()
    else:
        saida = _run(["bash", "-lc", "echo aGVsbG8= | base64 -d"])
        usou = "hello" in saida
    return {"tecnica": "Defense Evasion — LOLBin (certutil/base64)", "mitre": "T1140", "modifica": "nada",
            "executou": bool(usou), "bloqueado": None,
            "detalhe": "LOLBin invocado. Bom EDR alerta uso anômalo de certutil/base64."}


def _teste_persistencia() -> dict:
    """T1547.001 — cria uma chave Run BENIGNA e REMOVE (reversível). Testa alerta de persistência."""
    if not _WIN:
        return {"tecnica": "Persistence — chave Run (Windows)", "mitre": "T1547.001", "modifica": "—",
                "executou": False, "bloqueado": None, "detalhe": "teste específico de Windows"}
    nome = "ReconIA_BAS_Test"
    chave = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
    criado = False
    try:
        out = _run(["reg", "add", chave, "/v", nome, "/t", "REG_SZ", "/d", "cmd /c rem benign-bas-test", "/f"])
        criado = "__erro__" not in out
    finally:
        _run(["reg", "delete", chave, "/v", nome, "/f"])  # limpa sempre
    return {"tecnica": "Persistence — chave Run de inicialização", "mitre": "T1547.001", "modifica": "registro (criado e REMOVIDO)",
            "executou": criado, "bloqueado": None,
            "detalhe": "Chave Run criada e removida (reversível). EDR deveria alertar criação de persistência."}


_TESTES = {
    "eicar": _teste_av_eicar,
    "recon": _teste_recon,
    "lolbin": _teste_lolbin,
    "persistencia": _teste_persistencia,
}


def simular(testes: list[str] | None = None) -> dict:
    """Roda os testes atômicos seguros selecionados (ou todos). Retorna resultados + resumo."""
    nomes = testes or list(_TESTES)
    resultados = []
    for n in nomes:
        fn = _TESTES.get(n)
        if fn:
            try:
                resultados.append({"id": n, **fn()})
            except Exception as e:  # noqa: BLE001
                resultados.append({"id": n, "executou": False, "detalhe": f"erro: {e}"})

    detectaveis = [r for r in resultados if r.get("bloqueado") is True]
    return {
        "total": len(resultados),
        "detectados_bloqueados": len(detectaveis),
        "resultados": resultados,
        "aviso": "Testes benignos/reversíveis (Atomic Red Team). Verifique seu EDR/SIEM para os que não medem bloqueio aqui.",
    }
