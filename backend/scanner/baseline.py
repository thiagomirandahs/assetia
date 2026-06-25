"""Security Baseline + Score: mede a maturidade de hardening da maquina local.

Windows: Firewall, Defender, BitLocker, UAC, SMBv1, SMB signing, Secure Boot, RDP-NLA.
Linux: firewall (ufw/firewalld), updates automaticos, root-login SSH.
Cada check -> ok | falha | desconhecido. Score = % de 'ok' entre os conclusivos.
"""
import json
import logging
import platform
import subprocess

logger = logging.getLogger(__name__)

_WIN = platform.system().lower() == "windows"
_FLAGS = 0x08000000 if _WIN else 0  # CREATE_NO_WINDOW

# Script PowerShell que coleta tudo de uma vez e devolve JSON.
_PS_BASELINE = r"""
$r = [ordered]@{}
function Try-Bool($f){ try { [bool](& $f) } catch { 'desconhecido' } }
try { $fw = (Get-NetFirewallProfile -ErrorAction Stop | Where-Object {$_.Enabled -eq $false}).Count -eq 0; $r.firewall = $fw } catch { $r.firewall = 'desconhecido' }
try { $mp = Get-MpComputerStatus -ErrorAction Stop; $r.defender_antivirus = [bool]$mp.AntivirusEnabled; $r.defender_realtime = [bool]$mp.RealTimeProtectionEnabled } catch { $r.defender_antivirus='desconhecido'; $r.defender_realtime='desconhecido' }
try { $bl = (Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop).ProtectionStatus; $r.bitlocker = ($bl -eq 'On' -or $bl -eq 1) } catch { $r.bitlocker = 'desconhecido' }
try { $uac = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableLUA -ErrorAction Stop).EnableLUA; $r.uac = ($uac -eq 1) } catch { $r.uac = 'desconhecido' }
try { $smb1 = (Get-SmbServerConfiguration -ErrorAction Stop).EnableSMB1Protocol; $r.smb1_desativado = (-not $smb1) } catch { $r.smb1_desativado = 'desconhecido' }
try { $sig = (Get-SmbServerConfiguration -ErrorAction Stop).RequireSecuritySignature; $r.smb_signing = [bool]$sig } catch { $r.smb_signing = 'desconhecido' }
try { $sb = Confirm-SecureBootUEFI -ErrorAction Stop; $r.secure_boot = [bool]$sb } catch { $r.secure_boot = 'desconhecido' }
try { $nla = (Get-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication -ErrorAction Stop).UserAuthentication; $r.rdp_nla = ($nla -eq 1) } catch { $r.rdp_nla = 'desconhecido' }
$r | ConvertTo-Json -Compress
"""

# rotulo amigavel + dica por check
_META = {
    "firewall": ("Firewall ativo", "Ative o firewall em todos os perfis"),
    "defender_antivirus": ("Antivírus (Defender)", "Mantenha um antivírus ativo"),
    "defender_realtime": ("Proteção em tempo real", "Ative a proteção em tempo real"),
    "bitlocker": ("BitLocker (disco cifrado)", "Cifre o disco com BitLocker"),
    "uac": ("UAC (controle de conta)", "Mantenha o UAC habilitado"),
    "smb1_desativado": ("SMBv1 desativado", "Desative o SMBv1 (EternalBlue)"),
    "smb_signing": ("SMB signing exigido", "Exija assinatura SMB"),
    "secure_boot": ("Secure Boot", "Ative o Secure Boot na UEFI"),
    "rdp_nla": ("RDP com NLA", "Exija NLA no RDP"),
    "firewall_linux": ("Firewall ativo", "Ative ufw/firewalld"),
    "updates_auto": ("Updates automáticos", "Configure unattended-upgrades"),
    "ssh_root_off": ("SSH sem login root", "PermitRootLogin no"),
}


def _checks_windows() -> dict:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_BASELINE],
            capture_output=True, text=True, timeout=40, creationflags=_FLAGS,
        ).stdout.strip()
        return json.loads(out) if out else {}
    except Exception as e:  # noqa: BLE001
        logger.warning("baseline windows falhou: %s", e)
        return {}


def _checks_linux() -> dict:
    r = {}
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
        except Exception:  # noqa: BLE001
            return ""
    ufw = sh(["bash", "-lc", "ufw status 2>/dev/null || firewall-cmd --state 2>/dev/null"])
    r["firewall_linux"] = ("active" in ufw.lower() or "running" in ufw.lower()) if ufw.strip() else "desconhecido"
    upd = sh(["bash", "-lc", "test -f /etc/apt/apt.conf.d/20auto-upgrades && cat /etc/apt/apt.conf.d/20auto-upgrades"])
    r["updates_auto"] = ('"1"' in upd) if upd.strip() else "desconhecido"
    ssh = sh(["bash", "-lc", "grep -Ei '^PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null"])
    r["ssh_root_off"] = ("no" in ssh.lower()) if ssh.strip() else "desconhecido"
    return r


def baseline() -> dict:
    """Roda os checks de hardening da maquina local e calcula o score."""
    bruto = _checks_windows() if _WIN else _checks_linux()

    checks = []
    ok = total_conclusivos = 0
    for chave, valor in bruto.items():
        rotulo, dica = _META.get(chave, (chave, ""))
        if valor == "desconhecido":
            estado = "desconhecido"
        elif valor:
            estado = "ok"
            ok += 1
            total_conclusivos += 1
        else:
            estado = "falha"
            total_conclusivos += 1
        checks.append({"chave": chave, "rotulo": rotulo, "estado": estado, "dica": dica if estado != "ok" else ""})

    score = round(100 * ok / total_conclusivos) if total_conclusivos else 0
    if score >= 85:
        rotulo = "forte"
    elif score >= 60:
        rotulo = "razoável"
    elif score >= 35:
        rotulo = "fraco"
    else:
        rotulo = "crítico"

    return {
        "so": platform.system(),
        "score": score,
        "rotulo": rotulo,
        "ok": ok,
        "conclusivos": total_conclusivos,
        "checks": checks,
    }
