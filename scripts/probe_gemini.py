"""Sonda rapida: quais modelos Gemini esta chave consegue chamar (e quais tem cota)."""
import sys
sys.path.insert(0, ".")
from backend.core.config import get_settings
from google import genai

s = get_settings()
client = genai.Client(api_key=s.gemini_api_key)

print("=== modelos que suportam generateContent (primeiros 20) ===")
try:
    nomes = []
    for m in client.models.list():
        acoes = getattr(m, "supported_actions", None) or []
        if "generateContent" in acoes:
            nomes.append(m.name)
    for n in nomes[:20]:
        print("  ", n)
    print(f"  (total: {len(nomes)})")
except Exception as e:
    print("  erro ao listar:", e)

print("\n=== teste real (prompt trivial, sem tools) ===")
candidatos = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]
for modelo in candidatos:
    try:
        r = client.models.generate_content(model=modelo, contents="responda só: ok")
        txt = (r.text or "").strip().replace("\n", " ")[:40]
        print(f"  [OK ] {modelo} -> {txt!r}")
    except Exception as e:
        msg = str(e).replace("\n", " ")
        code = "429" if "429" in msg or "RESOURCE_EXHAUSTED" in msg else ("404" if "404" in msg or "NOT_FOUND" in msg else "ERR")
        print(f"  [{code}] {modelo} -> {msg[:90]}")
