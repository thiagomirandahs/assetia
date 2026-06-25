"""Diagnostico de rede: acha o equipamento que esta causando problema.

Combina: ping de gateway + externo (interno vs ISP), perda/latencia por host (categorizado
em desligado x instavel), e analise de ARP (spoofing / rogue / gateway personificado).

Implementacao SINCRONA com threads (evita o bug de cleanup de subprocess do asyncio
no Windows/Proactor). USO na sua propria rede.
"""
import logging
import platform
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from .arp import ler_tabela_arp
from .descoberta import detectar_redes
from .oui import fabricante

logger = logging.getLogger(__name__)

_WIN = platform.system().lower() == "windows"
_FLAGS_CRIAR = 0x08000000 if _WIN else 0  # CREATE_NO_WINDOW


def _gateway_padrao() -> str | None:
    """Le o gateway default do SO (Windows: route print; Linux/Mac: ip route)."""
    try:
        if _WIN:
            out = subprocess.run(["route", "print", "-4"], capture_output=True, text=True,
                                 timeout=8, creationflags=_FLAGS_CRIAR).stdout
            for ln in out.splitlines():
                m = re.match(r"\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)", ln)
                if m:
                    return m.group(1)
        else:
            out = subprocess.run(["ip", "route", "show", "default"], capture_output=True,
                                 text=True, timeout=8).stdout
            m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)
    except Exception as e:  # noqa: BLE001
        logger.warning("falha ao detectar gateway: %s", e)
    return None


def _ping_stats(ip: str, n: int = 4, timeout_ms: int = 1000) -> dict:
    """Pinga n vezes (sincrono) e retorna perda (%) e latencia media (ms)."""
    flags = ["-n", str(n), "-w", str(timeout_ms)] if _WIN else ["-c", str(n), "-W", str(max(1, timeout_ms // 1000))]
    try:
        cp = subprocess.run(["ping", *flags, ip], capture_output=True,
                            timeout=n * (timeout_ms / 1000) + 6, creationflags=_FLAGS_CRIAR)
        txt = cp.stdout.decode("latin-1", "ignore")  # latin-1 nunca falha
    except Exception:  # noqa: BLE001
        return {"ip": ip, "perda_pct": 100, "latencia_ms": None, "vivo": False}

    m_perda = re.search(r"\((\d+)%", txt) or re.search(r"(\d+)%\s*(?:packet )?loss", txt, re.IGNORECASE)
    perda = int(m_perda.group(1)) if m_perda else (0 if ("ttl=" in txt.lower()) else 100)

    m_rtt = re.search(r"=\s*[\d.]+/([\d.]+)/", txt)  # Linux: rtt min/avg/max
    if m_rtt:
        latencia = float(m_rtt.group(1))
    else:
        todas = re.findall(r"=\s*(\d+)\s*ms", txt)  # Windows: ultimo "= Nms" = Media
        latencia = float(todas[-1]) if todas else None

    return {"ip": ip, "perda_pct": perda, "latencia_ms": latencia, "vivo": perda < 100}


def _ip_unicast(ip: str) -> bool:
    if ip.startswith("255.") or ip == "0.0.0.0":
        return False
    try:
        return int(ip.split(".")[0]) < 224
    except (ValueError, IndexError):
        return False


def _mac_unicast(mac: str) -> bool:
    m = (mac or "").lower().replace("-", ":")
    if m in ("ff:ff:ff:ff:ff:ff", "", "00:00:00:00:00:00"):
        return False
    return not (m.startswith("01:00:5e") or m.startswith("33:33") or m.startswith("01:80:c2"))


def _mac_aleatorio(mac: str) -> bool:
    """MAC localmente administrado (randomizado) — típico de celular com privacidade de MAC.
    Bit 0x02 do 1º octeto setado. Esses devices dão perda alta normalmente (power-save)."""
    try:
        return bool(int((mac or "").replace("-", ":").split(":")[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False


def diagnosticar(cidr: str | None = None, *, n_pings: int = 6) -> dict:
    """Diagnostico completo. Retorna achados + suspeito principal + veredito."""
    redes = detectar_redes()
    gateway = _gateway_padrao()
    achados: list[dict] = []

    # 1) ARP: inverte mac -> ips (deteccao de spoofing/rogue)
    arp = ler_tabela_arp()  # {ip: mac}
    mac_para_ips: dict[str, list[str]] = defaultdict(list)
    for ip, mac in arp.items():
        if _ip_unicast(ip) and _mac_unicast(mac):
            mac_para_ips[mac.lower().replace("-", ":")].append(ip)
    suspeitos_arp = {mac: ips for mac, ips in mac_para_ips.items() if len(ips) >= 3}
    gw_mac = (arp.get(gateway) or "").lower().replace("-", ":") if gateway else ""
    gateway_personificado = bool(gw_mac and gw_mac in suspeitos_arp)

    # 2) pings: gateway, externo e hosts da ARP (em paralelo, com threads)
    hosts_arp = sorted({ip for ip in arp if _ip_unicast(ip) and ip != gateway},
                       key=lambda ip: tuple(int(o) for o in ip.split(".")))
    alvos = ([gateway] if gateway else []) + ["8.8.8.8"] + hosts_arp[:60]
    with ThreadPoolExecutor(max_workers=40) as ex:
        stats_lista = list(ex.map(lambda a: _ping_stats(a, n_pings), alvos))
    stats = {s["ip"]: s for s in stats_lista}
    gw_stats = stats.get(gateway) if gateway else None
    ext_stats = stats.get("8.8.8.8")

    # 3) achados de ARP (spoofing)
    suspeito_principal = None
    for mac, ips in sorted(suspeitos_arp.items(), key=lambda kv: -len(kv[1])):
        vend = fabricante(mac) or "fabricante desconhecido"
        eh_gw = mac == gw_mac
        det = (f"MAC {mac} ({vend}) responde por {len(ips)} IPs: {', '.join(ips[:6])}"
               + ("..." if len(ips) > 6 else "")
               + (" — e é o MAC do GATEWAY (forte indício de ARP spoofing/MITM!)" if eh_gw
                  else " — possível ARP spoofing, proxy-ARP ou rogue device."))
        achados.append({"tipo": "arp", "severidade": "critical" if eh_gw else "warning",
                        "detalhe": det, "mac": mac, "vendor": vend, "ips": ips, "gateway": eh_gw})
        if suspeito_principal is None:
            suspeito_principal = {"mac": mac, "vendor": vend, "ips": ips,
                                  "motivo": "gateway personificado (ARP spoofing)" if eh_gw else "responde por vários IPs"}

    # 4) categoriza perda: desligado (>=85%) x instavel (15-85%); e MAC aleatorio (celular) x real
    def _vd(s):
        mac = arp.get(s["ip"], "")
        return {**s, "mac": mac, "vendor": fabricante(mac) or "fab?", "aleatorio": _mac_aleatorio(mac)}

    flaky = sorted(
        (_vd(s) for ip, s in stats.items() if ip not in (gateway, "8.8.8.8") and 15 <= s["perda_pct"] < 85),
        key=lambda s: -s["perda_pct"])
    instaveis_reais = [s for s in flaky if not s["aleatorio"]]   # MAC global = equipamento "fixo"
    instaveis_random = [s for s in flaky if s["aleatorio"]]      # MAC aleatorio = provavel celular
    quase_off = [s for ip, s in stats.items() if ip not in (gateway, "8.8.8.8") and s["perda_pct"] >= 85]

    for s in instaveis_reais[:10]:
        achados.append({"tipo": "instavel", "severidade": "warning",
                        "detalhe": f"{s['ip']} ({s['vendor']}, MAC {s['mac'] or 'n/d'}) — {s['perda_pct']}% de perda, latência {s['latencia_ms']}ms",
                        "ip": s["ip"], "mac": s["mac"], "vendor": s["vendor"], "perda_pct": s["perda_pct"]})
    if instaveis_random:
        achados.append({"tipo": "info", "severidade": "info",
                        "detalhe": f"{len(instaveis_random)} host(s) com MAC aleatório e perda alta — provavelmente CELULARES em Wi-Fi power-save (normal, não é defeito)."})

    # 5) veredito
    gw_perda = gw_stats["perda_pct"] if gw_stats else 100
    ext_perda = ext_stats["perda_pct"] if ext_stats else 100
    if gateway_personificado:
        veredito = "🚨 GATEWAY personificado por ARP spoofing — provável causa da rede toda instável. Veja o suspeito principal."
    elif suspeitos_arp:
        veredito = "⚠️ Há um dispositivo respondendo por vários IPs (ARP anômalo) — forte candidato a estar bagunçando a rede toda."
    elif not gateway:
        veredito = "Não detectei o gateway. Verifique a configuração de rede."
    elif gw_perda >= 100:
        veredito = "Gateway INACESSÍVEL — problema entre você e o gateway (cabo/porta/switch local ou o próprio gateway)."
    elif ext_perda >= 100:
        veredito = "Gateway OK, mas SEM internet — o problema é no ISP/uplink, não num equipamento interno."
    elif gw_perda > 15:
        veredito = f"Gateway com {gw_perda}% de perda — link local instável (cabo/porta/switch até o gateway)."
    elif instaveis_reais:
        veredito = (f"Base da rede OK (gateway e internet saudáveis, sem ARP spoofing). "
                    f"{len(instaveis_reais)} EQUIPAMENTO(S) FIXO(S) instável(is) (perda intermitente) — principais suspeitos. Veja a lista.")
    elif instaveis_random:
        veredito = ("Base da rede OK e sem ARP spoofing. Os hosts com perda são quase todos CELULARES "
                    "(MAC aleatório) em Wi-Fi power-save — normal, não é defeito. Se ainda há problema, suspeite de "
                    "Wi-Fi (interferência/canal/AP saturado) ou rode o diagnóstico QUANDO o problema estiver acontecendo.")
    else:
        veredito = ("Base da rede OK (gateway, internet e ARP sem anomalia). Nenhum equipamento claramente instável. "
                    "Se ainda há problema, investigue camada física, Wi-Fi/interferência ou saturação de banda.")

    return {
        "rede": redes[0]["cidr"] if redes else cidr,
        "gateway": gateway,
        "gateway_mac": gw_mac or None,
        "gateway_stats": gw_stats,
        "externo_stats": ext_stats,
        "hosts_arp": len(hosts_arp),
        "instaveis": len(instaveis_reais),
        "celulares_flaky": len(instaveis_random),
        "quase_offline": len(quase_off),
        "suspeito_principal": suspeito_principal,
        "veredito": veredito,
        "achados": achados,
    }


def diagnosticar_sync(cidr: str | None = None, *, n_pings: int = 6) -> dict:
    return diagnosticar(cidr, n_pings=n_pings)
